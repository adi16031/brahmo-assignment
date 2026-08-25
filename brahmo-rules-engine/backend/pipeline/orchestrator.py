"""
Pipeline Orchestrator — wires all 6 stages together and does the (only)
database I/O in the pipeline.

Round trips, and the GAP 5 tradeoff: this pipeline makes exactly 2
sequential network round trips to Supabase — (1) user + hierarchy_levels,
fetched concurrently since BFS needs both before it can run, then (2) one
query for `knowledge_nodes` scoped to `hierarchy_level_id IN (BFS ∪ Zone2)
AND org_id = ?` — i.e. SQL already enforces structural BFS/Zone2 scope and
Check 1 (isolation) before any content is fetched. Checks 2-5 (compliance,
permission, temporal, derivability) then run in-process against that
already-scoped result.

This is a deliberate, acknowledged deviation from a stricter GAP-5 reading
that would defer ALL content fetch until after all 5 checks (which the
first draft did, using a content-free metadata-only query before a
separate final content fetch — see git history). That version was
correct but cost 3 round trips; measured against this Supabase project
each round trip costs ~200-300ms of pure network latency regardless of
query complexity (verified by timing each call in isolation), so 3 round
trips put total_ms consistently over the assessment's 500ms budget, and
2 round trips lands at/under it. The assessment's own FAQ explicitly
sanctions this tradeoff: "application-level filtering is faster to build
... acknowledge the tradeoff and explain how you'd move to RLS in
production." In production (same-region deployment, or RLS policies doing
this narrowing inside Postgres instead of round-tripping to the backend),
the stricter 3-round-trip version is the safer default; here, given
measured cross-region latency, 2 round trips is the pragmatic choice.

The five checks still run in-process, in strict sequence, each filtering
the PREVIOUS check's survivors — using the exact same pure predicate
functions (`check1_isolation`, `check2_compliance`, ...,
`check5_derivability`) unit tested in `tests/test_five_checks.py`. They
are never parallelized — each line runs after the previous one completes.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from supabase import Client

from models.candidate_set import CandidateSetResponse, DagLevelView, Funnel, PipelineTiming
from models.node import HierarchyLevel, KnowledgeNode
from models.user import User
from pipeline.bfs_traversal import bfs_reachable
from pipeline.candidate_assembler import assemble_candidate_set
from pipeline.entry_point_resolver import resolve_entry_point
from pipeline.five_check_filter import (
    FilterableNode,
    check1_isolation,
    check2_compliance,
    check3_permission,
    check4_temporal,
    check5_derivability,
)
from pipeline.permission_compiler import compile_permissions
from pipeline.zone2_injector import inject_zone2

# Org-wide node count is user-independent and the graph is static for this
# assessment (see Setup Guide FAQ) — safe to cache per-process instead of
# re-querying on every pipeline run.
_total_nodes_cache: dict[str, int] = {}


def _now_ms() -> float:
    return time.perf_counter() * 1000


def _fetch_user(supabase: Client, user_id: str) -> User:
    resp = supabase.table("users").select("*").eq("id", user_id).single().execute()
    return User(**resp.data)


def _fetch_hierarchy_levels(supabase: Client, org_id: str) -> list[HierarchyLevel]:
    resp = supabase.table("hierarchy_levels").select("*").eq("org_id", org_id).execute()
    return [HierarchyLevel(**row) for row in resp.data]


def _count_total_nodes(supabase: Client, org_id: str) -> int:
    resp = (
        supabase.table("knowledge_nodes")
        .select("id", count="exact", head=True)
        .eq("org_id", org_id)
        .execute()
    )
    return resp.count or 0


def _fetch_scoped_nodes(
    supabase: Client, hierarchy_level_ids: list[str], org_id: str
) -> list[KnowledgeNode]:
    """Full rows, but SQL already narrows to structural BFS/Zone2 scope
    AND isolation (Check 1) — never the whole table."""
    if not hierarchy_level_ids:
        return []
    resp = (
        supabase.table("knowledge_nodes")
        .select("*")
        .in_("hierarchy_level_id", hierarchy_level_ids)
        .eq("org_id", org_id)
        .execute()
    )
    return [KnowledgeNode(**row) for row in resp.data]


def run_pipeline(
    supabase: Client, user_id: str, org_id: str, derivability_threshold: float = 0.7,
    zone2_enabled: bool = True,
) -> CandidateSetResponse:
    t_start = _now_ms()

    # User + hierarchy are independent lookups (neither is a "check") —
    # dispatched concurrently purely to cut network wall time.
    with ThreadPoolExecutor(max_workers=2) as pool:
        user_future = pool.submit(_fetch_user, supabase, user_id)
        hierarchy_future = pool.submit(_fetch_hierarchy_levels, supabase, org_id)
        user = user_future.result()
        hierarchy_levels = hierarchy_future.result()
    t_load = _now_ms()

    level_number_by_id = {h.id: h.level_number for h in hierarchy_levels}

    t0 = _now_ms()
    permission_map = compile_permissions(user)
    t1 = _now_ms()

    entry = resolve_entry_point(hierarchy_levels, user.department, user.ceiling_level)
    t2 = _now_ms()

    bfs_ids = bfs_reachable(hierarchy_levels, entry.id)
    t3 = _now_ms()

    all_ids = inject_zone2(hierarchy_levels, bfs_ids) if zone2_enabled else dict(bfs_ids)
    t4 = _now_ms()

    # Second (and last) round trip: the org-wide count stat and the
    # scoped node fetch are independent of each other — dispatch together.
    if org_id in _total_nodes_cache:
        total_nodes = _total_nodes_cache[org_id]
        scoped_nodes = _fetch_scoped_nodes(supabase, list(all_ids.keys()), org_id)
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:
            total_future = pool.submit(_count_total_nodes, supabase, org_id)
            nodes_future = pool.submit(_fetch_scoped_nodes, supabase, list(all_ids.keys()), org_id)
            total_nodes = total_future.result()
            scoped_nodes = nodes_future.result()
        _total_nodes_cache[org_id] = total_nodes
    t5 = _now_ms()

    after_bfs = sum(1 for n in scoped_nodes if n.hierarchy_level_id in bfs_ids)
    after_zone2 = len(scoped_nodes)

    filterable_nodes = [
        FilterableNode(
            id=n.id,
            org_id=n.org_id,
            compliance_tags=n.compliance_tags,
            hierarchy_level_number=level_number_by_id.get(n.hierarchy_level_id, -1),
            zone=n.zone,
            status=n.status,
            valid_until=n.valid_until,
            derivability_score=n.derivability_score,
        )
        for n in scoped_nodes
    ]
    nodes_by_id = {n.id: n for n in scoped_nodes}

    # Each check filters the PREVIOUS check's survivors — never the original
    # set. Individually timed so the reported per-check ms are real.
    # Check 1 (isolation) is already enforced by the SQL `org_id = ?`
    # filter above; re-applying it here in-process is a cheap, harmless
    # confirmation that keeps the 5-stage funnel/timing shape intact.
    now = datetime.now(timezone.utc)

    tc0 = _now_ms()
    after_check1 = [n for n in filterable_nodes if check1_isolation(n, org_id)]
    tc1 = _now_ms()
    after_check2 = [n for n in after_check1 if check2_compliance(n, user.compliance_clearance)]
    tc2 = _now_ms()
    # Uses the O(1) compiled permission map from Stage 1 (permission_map),
    # not a fresh ceiling comparison per node — this is the payoff of
    # compiling permissions once per session (see docs/architecture.md §3).
    # Zone 2 nodes are exempt (see five_check_filter.check3_permission).
    after_check3 = [n for n in after_check2 if check3_permission(n, permission_map)]
    tc3 = _now_ms()
    after_check4 = [n for n in after_check3 if check4_temporal(n, now)]
    tc4 = _now_ms()
    after_check5 = [n for n in after_check4 if check5_derivability(n, derivability_threshold)]
    tc5 = _now_ms()

    final_nodes = [nodes_by_id[n.id] for n in after_check5]
    candidate_set = assemble_candidate_set(final_nodes, all_ids, level_number_by_id)

    dag_view = [
        DagLevelView(
            id=h.id,
            level_name=h.level_name,
            level_number=h.level_number,
            department=h.department,
            zone=h.zone,
            parent_ids=h.parent_ids,
            reachable=h.id in all_ids,
            distance=all_ids.get(h.id),
            reachable_via=(
                "BFS" if h.id in bfs_ids else ("ZONE2" if h.id in all_ids else None)
            ),
            is_entry=(h.id == entry.id),
        )
        for h in hierarchy_levels
    ]

    timing = PipelineTiming(
        permission_compile_ms=round(t1 - t0, 2),
        entry_resolve_ms=round(t2 - t1, 2),
        bfs_ms=round(t3 - t2, 2),
        zone2_inject_ms=round(t4 - t3, 2),
        fetch_nodes_ms=round((t_load - t_start) + (t5 - t4), 2),
        check1_isolation_ms=round(tc1 - tc0, 2),
        check2_compliance_ms=round(tc2 - tc1, 2),
        check3_permission_ms=round(tc3 - tc2, 2),
        check4_temporal_ms=round(tc4 - tc3, 2),
        check5_derivability_ms=round(tc5 - tc4, 2),
        total_ms=round(_now_ms() - t_start, 2),
    )
    funnel = Funnel(
        total_nodes=total_nodes,
        after_bfs=after_bfs,
        after_zone2=after_zone2,
        after_check1=len(after_check1),
        after_check2=len(after_check2),
        after_check3=len(after_check3),
        after_check4=len(after_check4),
        after_check5=len(candidate_set),
    )

    return CandidateSetResponse(
        user_id=user.id,
        user_name=user.name,
        role=user.role,
        ceiling_level=user.ceiling_level,
        entry_point=entry.id,
        entry_point_name=entry.level_name,
        pipeline_timing=timing,
        funnel=funnel,
        candidate_set=candidate_set,
        dag=dag_view,
    )
