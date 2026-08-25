# Implementation Plan: BRAHMO Rules Engine (BFS + 5-Check Filter Pipeline)

Status: planning only, no code written yet.
Source specs: `ASSESSMENT_01_BFS_Traversal_5Check_Filter.md`, `ASSESSMENT_01_SETUP_GUIDE.md`

---

## 1. Stack Decisions (resolving the assessment's open choices)

| Decision | Choice | Rationale |
|---|---|---|
| Backend | Python + FastAPI | Pipeline logic (BFS, graph ops) is clearer in Python; assessment lists it as primary path; easy to unit test each stage in isolation. |
| Frontend | Next.js (React) + TypeScript + Tailwind | Matches provided project structure exactly. |
| DB access for Checks 1-4 | SQL WHERE clauses via Supabase Python client (`postgrest` filters), NOT fetch-all-then-filter | Required by GAP 5 — restricted data must never leave the DB before permission is checked. Acknowledged tradeoff vs full RLS (see §7). |
| Check 5 (derivability) | Pre-computed `derivability_score` column, threshold filter also pushed to SQL (`WHERE derivability_score < 0.7`) | Keeps ALL 5 checks as SQL predicates — no LLM, no per-row Python filtering. |
| BFS traversal | In-memory over `hierarchy_levels.parent_ids`, fetched once (15 rows, cheap) | Hierarchy table is tiny regardless of node count — safe to load fully; `knowledge_nodes` (large table) is never fetched pre-filter. |
| RLS vs application-level filtering | Application-level for the demo, with RLS documented as the production path | Faster to build in the time budget; explicitly allowed by FAQ if tradeoff is acknowledged in `architecture.md`. |

---

## 2. Architecture Recap (data flow contract)

```
User selected → Permission Compiler → Entry Point Resolver → BFS (upward, hierarchy_levels)
  → collects reachable hierarchy_level_ids + distances
  → Zone 2 Injection (add all zone=2 hierarchy_level_ids)
  → Query knowledge_nodes WHERE hierarchy_level_id IN (reachable ∪ zone2)
  → Check 1 Isolation (SQL)
  → Check 2 Compliance (SQL)
  → Check 3 Permission (SQL, using compiled ceiling)
  → Check 4 Temporal (SQL)
  → Check 5 Derivability (SQL)
  → Candidate Set Assembler (annotate: distance_from_entry, compression_hint, zone)
  → JSON response (candidate_set + funnel counts + timing)
```

Key subtlety: BFS operates on **`hierarchy_levels`** (15 rows, the DAG skeleton), not on `knowledge_nodes` directly. Once the reachable set of `hierarchy_level_id`s is known, `knowledge_nodes` is queried once with `hierarchy_level_id = ANY(reachable_ids)` — this is what keeps Checks 1-4 as pure SQL predicates on a single filtered query, and is also the answer to the scalability question (traversal cost is bounded by DAG depth/branching, not by knowledge_nodes row count).

Distance-from-entry is captured during BFS per `hierarchy_level_id`, then attached to each node by its hierarchy level after retrieval (Zone 2 nodes get distance = BFS depth of `HL-GLOBAL` from entry, or a sentinel if unreachable structurally — treat as a fixed "injected" distance, e.g. max BFS depth + 1, documented in architecture.md).

---

## 3. Project Structure

```
brahmo-rules-engine/
├── README.md
├── .env.example
├── docs/
│   └── architecture.md
├── backend/
│   ├── main.py
│   ├── config.py                     # Supabase client init
│   ├── pipeline/
│   │   ├── permission_compiler.py
│   │   ├── entry_point_resolver.py
│   │   ├── bfs_traversal.py
│   │   ├── zone2_injector.py
│   │   ├── five_check_filter.py
│   │   ├── candidate_assembler.py
│   │   └── orchestrator.py           # wires all stages, times each one
│   ├── models/
│   │   ├── user.py
│   │   ├── node.py
│   │   └── candidate_set.py
│   ├── routers/
│   │   └── pipeline.py               # POST /api/pipeline/run, GET /api/users
│   └── tests/
│       ├── test_bfs.py
│       ├── test_permission_compiler.py
│       ├── test_five_checks.py
│       └── test_pipeline.py          # end-to-end, asserts expected counts per §6
├── frontend/
│   └── src/
│       ├── app/page.tsx
│       ├── components/
│       │   ├── UserSelector.tsx
│       │   ├── FilterFunnel.tsx
│       │   ├── DAGViewer.tsx
│       │   ├── CandidateTable.tsx
│       │   └── ComparisonView.tsx
│       └── lib/{supabase.ts, types.ts, api.ts}
└── supabase/
    ├── schema.sql
    └── seed.sql
```

---

## 4. Build Order (maps to the 8-hour budget in the Setup Guide)

1. **Environment + Supabase project** (0.5h) — create project, run `schema.sql`, run `seed.sql`, verify `SELECT COUNT(*)` = 50 nodes / 7 users.
2. **Backend skeleton** (0.25h) — FastAPI app, Supabase client, `/api/users` returns the 7 seeded users.
3. **Permission Compiler** (0.5h)
   - Input: user row (`role`, `ceiling_level`, `write_ceiling`, `compliance_clearance`).
   - Output: `{level: {can_read, can_write}}` for levels 1-15, built by rule per role (VIEWER/EDITOR/HOD/ADMIN/QUALITY/AUDITOR — must be data-driven off `role` + `ceiling_level`, not per-name branching, so unseen roles still work).
   - Unit test: assert monotonic behavior (lower level number = higher authority in this schema; `hierarchy_level >= ceiling_level` is the passing condition per Check 3).
4. **Entry Point Resolver** (0.25h) — `hierarchy_levels WHERE department = user.department` picks the deepest (highest `level_number`) matching row as entry; HOD/no-department-match users fall back to their department's top-level node. Document the exact rule since Setup Guide's Vikram example (ceiling L4, entry at his HOD dept node) implies entry ≠ ceiling level.
5. **BFS Traversal** (1.0h) — most critical piece.
   - Load all `hierarchy_levels` for the org once (15 rows).
   - Build a `children_by_parent` or reverse-traverse using `parent_ids` arrays directly (since edges point child→parents, "walking up" = following `parent_ids`).
   - BFS with FIFO queue + `visited: dict[node_id, distance]`, starting at entry point distance 0.
   - Multi-parent case: a level's `parent_ids` may contain multiple ids (e.g. `HL-08-POST-TKR` → both `HL-05-ORTHO` and `HL-05-SURG`); enqueue both, dedupe via visited set, keep the **minimum** distance if reached twice.
   - Cycle safety: visited set makes this loop-safe by construction; additionally, note (for the thinking-guide answer) an insert-time validation option (reject an edge if adding it creates a path back to itself via DFS) — call out as a documented decision, optional to implement given time budget.
   - Output: set of reachable `hierarchy_level_id`s with distances.
   - Unit test: verify Priya's reach path Ortho Ward → Ortho Gen → Ortho Dept → Clinical → Hospital, and that Cardiology/Medicine/Paeds/ICU level ids are absent.
6. **Zone 2 Injection** (0.25h) — add `HL-GLOBAL` (and any other `zone=2` hierarchy levels) to the reachable set post-BFS, with a fixed injected distance; merge before querying nodes.
7. **Node retrieval + Five-Check Filter** (1.5h) — build incrementally, verifying funnel counts after each check:
   - Single Supabase query: `knowledge_nodes.select().in_("hierarchy_level_id", reachable_ids)` → this is "BFS + Zone2" count.
   - Check 1: `.eq("org_id", user.org_id)`.
   - Check 2: exclude rows where `compliance_tags` overlaps `user.blocked_tags` (blocked_tags = all tags NOT in `user.compliance_clearance`, or simpler: exclude if any tag in `compliance_tags` is not in clearance — implement as Python set check on the already-narrow row set returned by step above, OR push down via `not compliance_tags && array[...]` if feasible in one query; decide during implementation, document choice).
   - Check 3: `.gte("hierarchy_level", user.ceiling_level)` — note hierarchy_level here refers to the node's own level number (join through `hierarchy_level_id` → `hierarchy_levels.level_number`, or denormalize by also filtering in Python using the compiled permission map for O(1) lookups per node, per Problem 5 in the thinking guide).
   - Check 4: `.neq("status", "SUPERSEDED")` and `(valid_until IS NULL OR valid_until > now())`.
   - Check 5: `.lt("derivability_score", threshold)` where threshold comes from `organizations.config.derivability_threshold` (0.7 default, per-org configurable — matches FAQ).
   - Record count after each stage into the `funnel` object; record elapsed ms per stage into `pipeline_timing`.
   - Test after each check individually against expected counts (§6).
8. **Candidate Set Assembler** (0.25h) — annotate surviving nodes: `distance_from_entry` (from BFS map, or injected-distance for Zone 2), `compression_hint` (0-1→FULL, 2→COMPRESSED, 3+→CONSTRAINT_ONLY), pass through `type`, `importance`, `zone`, `hierarchy_level`, `department`.
9. **Orchestrator + API endpoint** (0.25h) — `POST /api/pipeline/run {user_id}` runs all stages, returns the full JSON contract from the Setup Guide (user, entry_point, pipeline_timing, funnel, candidate_set).
10. **Frontend** (1.5h)
    - `UserSelector`: dropdown of 7 users + "Run Pipeline" button.
    - `FilterFunnel`: bar/funnel chart of `funnel` counts (Total → BFS → +Zone2 → after each check) — must visually communicate the narrowing.
    - `DAGViewer`: render the 15-level hierarchy tree, color-code reachable (●) vs unreachable (○) vs Zone 2 (◆) for the current user.
    - `CandidateTable`: list final nodes grouped by `type`, showing importance/distance/zone/compression_hint.
    - `ComparisonView`: run pipeline for 2-3 users side by side (Priya/Vikram/Suresh), show counts + a checklist of which categories each can/can't see.
    - Pipeline timing displayed (total + per-stage breakdown from `pipeline_timing`).
    - A toggle to disable Zone 2 injection (for Demo Scenario 4).
11. **End-to-end scenario verification + innovation pass** (0.5h) — run all 4 demo scenarios, verify §6 numbers, implement one "thinking guide" innovation (see §8), write `docs/architecture.md`.

---

## 5. Data-Driven Correctness Rules (to avoid hardcoding / pass the surprise test)

- Permission compilation must be a pure function of `(role, ceiling_level, write_ceiling)` — no `if user.name == "Priya"` anywhere.
- Entry point resolution must be a pure function of `(user.department)` against `hierarchy_levels` — a brand-new department value must resolve automatically as long as a matching `hierarchy_levels.department` row exists.
- Compliance check must be a pure function of `(node.compliance_tags, user.compliance_clearance)` — an AUDITOR with `compliance_clearance = {'MNPI'}` must automatically see MNPI nodes without special-casing the AUDITOR role name.
- No response field should ever indicate *why* a node is missing or that nodes were removed — funnel counts show aggregate numbers only, never per-node exclusion reasons in the API response (that's for internal logging/audit_log only, not the user-facing payload).

---

## 6. Verification Checklist (expected counts, from Setup Guide "Expected Pipeline Results")

- [ ] Priya (VIEWER, L10, ortho): BFS ~20 → +Zone2 ~30 → after checks ~15
- [ ] Vikram (HOD, L4, ortho): BFS ~25 → +Zone2 ~35 → after checks ~22
- [ ] Suresh (ADMIN, L1): BFS 50 (all) → after checks ~40
- [ ] Priya's set has zero Cardiology/Paeds/ICU/Medicine-only nodes
- [ ] Priya's set has zero MNPI-tagged nodes (N-O11, N-O12 excluded)
- [ ] Priya's set has zero SUPERSEDED nodes (N-M08 excluded structurally — also outside her BFS reach)
- [ ] Priya's set has zero high-derivability nodes (N-D01/03/04 excluded)
- [ ] Vikram sees N-O11 but not N-O12 (needs ADMIN-level clearance)
- [ ] Suresh sees N-A01, N-A02, N-O11, N-O12, N-C04
- [ ] Same pipeline code path for all users — only user_id input changes
- [ ] A never-before-used 8th user (e.g. QUALITY or AUDITOR role) produces a distinct, sensible count with zero code changes

---

## 7. Answers to Prepare for Demo Q&A (from assessment doc)

- **"Why sequential, not parallel checks?"** Each check narrows the input set for the next; Check 3 must not evaluate nodes Check 2 already excluded — running in parallel would require each check to redundantly re-derive the prior checks' exclusions, and risks a node passing Check 3 in isolation that Check 2 should have blocked.
- **"What happens at 15,000 nodes?"** BFS cost is bounded by the user's reachable subgraph (depth × branching of the DAG), not total node count — Priya's traversal touches the same ~20 hierarchy levels whether the org has 50 or 15,000 knowledge nodes. Checks 1-4 are SQL predicates that scale with indexes (`idx_nodes_hierarchy`, `idx_nodes_compliance`, `idx_nodes_status`). Derivability is pre-computed at write time, not query time.
- **"Show a node Priya can't see but Vikram can, why?"** N-O11 (Ortho Department Budget) — `compliance_tags = {'MNPI'}`, `hierarchy_level` corresponds to L5; Priya's ceiling is L10 (numerically higher = more restrictive per this schema's `>=` check) and she has no MNPI clearance either way; Vikram's ceiling is L4 and HOD role grants broader read access.
- **"What if someone bypasses the API and queries the database directly?"** With application-level filtering (our demo choice) this is a real gap — call this out explicitly in `architecture.md` as the reason production should move Checks 1-4 into RLS policies keyed off `auth.uid()`/session claims, so even a direct DB connection is constrained.

---

## 8. Innovation Candidates (pick ONE, time-permitting — 15% of grade)

Ranked by effort-to-payoff given the remaining time budget:

1. **Derivability scoring heuristic beyond the static seed column** — e.g., a lightweight rule: flag as derivable if content lacks organization-specific markers (no "Supra", no dosage-with-named-drug-decision-context, no patient name) combined with length/genericness heuristics; compute at seed-load time as a batch step, store back into `derivability_score`. Demonstrates Problem 1 without any runtime LLM call.
2. **Insert-time cycle validation** — before inserting/updating a `hierarchy_levels.parent_ids` edge, run a DFS from the new parent to confirm the child isn't already an ancestor; reject with a clear error if so. Directly answers Problem 4.
3. **RLS policy implementation** as an alternative/additional path for Checks 1 and 3 (isolation + permission), with a toggle to compare app-level vs RLS-enforced timing — directly answers Problem 3 with a working artifact instead of just prose.

Recommendation: do #1 (cheapest, most visibly demoable in the funnel/candidate table) and document #2 and #3 as "considered, documented in architecture.md" if time runs out.

---

## 9. `docs/architecture.md` Outline (write last, ~20 min)

1. Data flow diagram (ASCII, mirrors §2 above)
2. Why BFS operates on `hierarchy_levels` not `knowledge_nodes` directly (scalability argument)
3. Permission compiler data structure + O(1) rationale (Problem 5)
4. Multi-parent handling + visited-set proof (Problem 2)
5. SQL-pushdown rationale for Checks 1-4 + RLS tradeoff acknowledgment (Problem 3)
6. Cycle prevention strategy (Problem 4)
7. Derivability approach chosen (Problem 1) + innovation implemented
8. Known limitations / what a production version would add (RLS, real-time graph updates, multi-org)

---

## 10. Out of Scope (explicitly, per assessment)

- No Composition Agent (prompt assembly downstream of candidate set)
- No real authentication — dropdown user selection only
- No knowledge node editor/CRUD UI
- No LLM calls anywhere in the pipeline
- No real-time graph mutation handling
