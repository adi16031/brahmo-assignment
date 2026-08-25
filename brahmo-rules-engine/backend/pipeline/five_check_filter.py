"""
Five-Check Sequential Filter — Stage 5.

Single source of truth for the 5 pass/fail predicates. Each predicate is
a pure function of (node, user-derived criteria) — no role-name branching
anywhere, so a brand-new role/department/compliance-clearance combination
is handled correctly with zero code changes (only data changes).

These same predicates are what `orchestrator.py` calls directly (not a
reimplementation — the live pipeline imports these functions), so there is
exactly one definition of "what passes," exercised by both the demo and
`tests/test_five_checks.py`.

CRITICAL: checks run sequentially. Check N's input is Check (N-1)'s
surviving set, not the original set — see `run_five_checks`.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from models.user import PermissionMap
from pipeline.permission_compiler import can_read_level


@dataclass
class FilterableNode:
    id: str
    org_id: str
    compliance_tags: list[str]
    hierarchy_level_number: int
    zone: int
    status: str
    valid_until: Optional[str]  # ISO 8601 string or None
    derivability_score: float


def check1_isolation(node: FilterableNode, org_id: str) -> bool:
    return node.org_id == org_id


def check2_compliance(node: FilterableNode, compliance_clearance: list[str]) -> bool:
    # Node passes iff every tag it carries is one the user is cleared for
    # (compliance_tags is a subset of compliance_clearance).
    return set(node.compliance_tags).issubset(set(compliance_clearance))


def check3_permission(node: FilterableNode, permission_map: PermissionMap) -> bool:
    # Zone 2 (global) nodes are exempt from the seniority ceiling: they are
    # hospital-wide safety constraints ("never combine Warfarin with
    # NSAIDs") that apply to every user who can already reach the org at
    # all — not privileged information gated by organizational rank. This
    # is required by the assessment's own Zone-2 demo scenario, which
    # states Zone 2 nodes are "within Priya's permission ceiling" even
    # though her ceiling (level 10, a ward-level VIEWER) sits numerically
    # below the level Zone 2 content is attached to (level 3, Global
    # Constraints) — i.e. the ceiling comparison below would otherwise
    # incorrectly exclude them for every VIEWER-tier user. Zone 1
    # (addressed/department) content still goes through the real O(1)
    # compiled-permission lookup from Stage 1.
    if node.zone == 2:
        return True
    return can_read_level(permission_map, node.hierarchy_level_number)


def check4_temporal(node: FilterableNode, now: Optional[datetime] = None) -> bool:
    if node.status == "SUPERSEDED":
        return False
    if node.valid_until is None:
        return True
    now = now or datetime.now(timezone.utc)
    valid_until = datetime.fromisoformat(node.valid_until.replace("Z", "+00:00"))
    return valid_until > now


def check5_derivability(node: FilterableNode, threshold: float) -> bool:
    return node.derivability_score < threshold


def run_five_checks(
    nodes: list[FilterableNode],
    org_id: str,
    compliance_clearance: list[str],
    permission_map: PermissionMap,
    derivability_threshold: float,
    now: Optional[datetime] = None,
) -> dict:
    after_check1 = [n for n in nodes if check1_isolation(n, org_id)]
    after_check2 = [n for n in after_check1 if check2_compliance(n, compliance_clearance)]
    after_check3 = [n for n in after_check2 if check3_permission(n, permission_map)]
    after_check4 = [n for n in after_check3 if check4_temporal(n, now)]
    after_check5 = [n for n in after_check4 if check5_derivability(n, derivability_threshold)]

    return {
        "after_check1": after_check1,
        "after_check2": after_check2,
        "after_check3": after_check3,
        "after_check4": after_check4,
        "after_check5": after_check5,
    }
