# Architecture

## 1. Data flow

```
User selected
  → Permission Compiler   (compile_permissions — O(1) map, pure function of ceiling_level/write_ceiling)
  → Entry Point Resolver  (resolve_entry_point — department node closest to ceiling_level, see §3)
  → BFS Traversal         (bfs_reachable — entry's ANCESTORS (up) ∪ entry's DESCENDANT SUBTREE (down), see §2)
  → Zone 2 Injection      (inject_zone2 — adds zone=2 levels, distance inherited from nearest visited parent)
  → knowledge_nodes fetch, scoped to reachable hierarchy_level_ids AND org_id (Check 1) in one query
  → Check 1 Isolation     (org_id = ? — already enforced by the fetch above; re-applied in-process for the funnel)
  → Check 2 Compliance    (compliance_tags ⊆ user.compliance_clearance)
  → Check 3 Permission    (O(1) permission_map lookup; Zone 2 nodes exempt, see §5)
  → Check 4 Temporal      (status != SUPERSEDED AND (valid_until IS NULL OR valid_until > now()))
  → Check 5 Derivability  (derivability_score < threshold)
  → Candidate Set Assembler (distance_from_entry, compression_hint)
  → JSON response (candidate_set + funnel counts + per-stage timing + dag view)
```

Each stage is its own module under `backend/pipeline/`, kept as pure functions
wherever possible (`bfs_traversal.py`, `zone2_injector.py`,
`entry_point_resolver.py`, `permission_compiler.py`, `five_check_filter.py`,
`candidate_assembler.py`) so they're unit-testable without a database.
`orchestrator.py` is the only module that touches Supabase; the five checks
themselves are the exact functions exercised by `tests/test_five_checks.py`,
not a separate SQL reimplementation, so there is one source of truth for
"what passes."

This document records several places where the assessment's own materials
(the flow-diagram narrative, the illustrative candidate-set JSON, the
Expected Pipeline Results table) turned out to be internally inconsistent
with each other, or with the literal seed data, once actually implemented
and run against a live database. Each is called out explicitly below with
the concrete evidence, because the fix in each case required deviating from
a literal reading of one part of the spec in favor of another — a judgment
call worth making visible rather than silent.

## 2. BFS is two-directional: ancestors ∪ entry's own descendant subtree

The assessment's flow diagram narrates BFS as "walks UP the DAG." Taken
literally and in isolation, this cannot be the complete algorithm: the
Expected Pipeline Results table requires Admin Suresh, entering at the
Hospital root (`HL-01`, which has **zero parents**), to reach **all 50
nodes**. A parentless root can only reach anything by walking *down*; pure
upward-only traversal from it reaches nothing but itself. This is
independently confirmed by the same table's requirement that Dr. Vikram,
entering at the Orthopaedics *department* level, reaches the multi-parent
`HL-08-POST-TKR` node underneath it — which is a *child* of his entry, not
an ancestor.

The reconciled rule, implemented in `bfs_traversal.py`:

```
reachable(entry) = ancestors(entry)  [walk up via parent_ids]
                 ∪ descendants(entry) [walk down via reverse parent_ids]
```

Both passes are seeded **only** by the entry node and never cross-propagate,
which is what keeps department isolation intact:

- The downward pass continues down from whatever it discovers (descendants
  of descendants), but never walks back up from a discovered descendant.
  Without this restriction, discovering `HL-08-POST-TKR` (which also lists
  Surgery as a parent) while exploring down from Vikram's Orthopaedics entry
  would let him walk up into the Surgery department too.
- The upward pass continues up from whatever it discovers (ancestors of
  ancestors), but never walks back down from a discovered ancestor. Without
  this restriction, reaching Clinical Division as an ancestor of Ortho Ward
  would let a ward-level nurse walk down into every other department under
  Clinical Division (Cardiology, Medicine, ...).

Verified in `tests/test_bfs.py`:
`test_bfs_walks_upward_from_ward_to_hospital_and_down_to_own_patient`,
`test_dept_level_entry_reaches_sub_specialty_descendants_but_not_sibling_dept`,
`test_root_entry_reaches_the_entire_graph`. Both passes share one `visited`
dict and use a FIFO queue, so multi-parent/multi-child nodes are processed
exactly once and an accidental cycle in either direction terminates instead
of looping forever
(`test_visited_set_prevents_infinite_loop_on_accidental_cycle`).

This also is the answer to the scalability question: BFS operates on
`hierarchy_levels` (at most ~15 rows per org), not `knowledge_nodes` (the
table that actually scales, 50 today, 15,000 at hospital-chain scale) —
`knowledge_nodes` is only ever queried afterward, filtered to the resulting
small id set. A user's reachable subgraph size doesn't grow with total
graph size.

## 3. Entry point resolution uses ceiling_level, not just department

A department is not a single node — "ortho" spans levels 5 (department), 8
(sub-specialty), 10 (ward), and 12 (patient records) in the seed hierarchy.
Resolving "Nurse Priya's entry point" from `department == "ortho"` alone is
ambiguous; the Expected Results table requires her entry at the *ward*
(level 10) while requiring Dr. Vikram — same department, HOD role — to
enter at the *department* itself (level 5).

`entry_point_resolver.py` resolves this using the exact same `ceiling_level`
field Check 3 uses: among a user's department's hierarchy_levels rows, pick
the **shallowest** one they're still permitted to read
(`level_number >= ceiling_level`) — i.e. "the most senior position in your
own department your ceiling allows you to occupy":

```
Priya  (ortho, ceiling 10) -> candidates {5,8,8,10,12} with level>=10: {10,12} -> shallowest: 10 (Ward)       ✓
Vikram (ortho, ceiling  4) -> candidates {5,8,8,10,12} with level>=4:  {5,8,8,10,12} -> shallowest: 5 (Dept)  ✓
```

If no department node meets the ceiling (a ceiling stricter than everything
in that department), it falls back to the deepest available node in that
department. If the department has no hierarchy_levels rows at all (e.g. a
Pharmacist before a Pharmacy branch exists in the DAG), it falls back to the
org root — that user's candidate set then comes almost entirely from Zone 2.

## 4. Permission compiler: one role-agnostic rule

The AI-starter-prompt text describes per-role read/write behavior ("VIEWER:
read >= ceiling", "HOD: read all levels", "ADMIN: read/write everything").
`permission_compiler.py` implements a single, uniform, role-agnostic rule
instead of branching on role name:

```
can_read(level)  = level >= ceiling_level
can_write(level) = write_ceiling is not None and level >= write_ceiling
```

VIEWER's "can't write anything" falls out naturally from `write_ceiling`
being `None` in the seed data — no code path ever checks the string
`"VIEWER"`. This is what makes the pipeline pass the "surprise new role"
test: a brand-new role works correctly as long as it has `ceiling_level`
and optionally `write_ceiling`. `compile_permissions()` builds this
`{level_number: {can_read, can_write}}` map once per pipeline run — an O(1)
lookup reused by Check 3 for every node, instead of a query per node.

## 5. Check 3 exempts Zone 2 nodes from the ceiling comparison

Applying `level_number >= ceiling_level` literally to **every** node,
including Zone 2 (global) content, contradicts the assessment's own Zone 2
demo scenario, which states those nodes are "within Priya's permission
ceiling" — yet Zone 2 content is attached to `HL-GLOBAL` at level 3, and
Priya's ceiling is 10 (`3 >= 10` is false). Excluding Zone 2 content for
every VIEWER-tier user would also make the "Zone 2 saves lives" demo
(toggle Zone 2 off/on, show the drug-safety nodes appear/disappear)
impossible to show for the very user the scenario is written around.

`five_check_filter.check3_permission` therefore treats Zone 2 as exempt from
the seniority ceiling:

```python
if node.zone == 2:
    return True  # hospital-wide safety constraint — applies to everyone
return can_read_level(permission_map, node.hierarchy_level_number)
```

This is a defensible real-world policy, not just a workaround: "don't
combine Warfarin with NSAIDs" is not privileged information gated by
organizational rank — it must reach every clinical user regardless of
seniority. Zone 1 (department-specific) content still goes through the real
ceiling check via the compiled permission map. Verified in
`tests/test_five_checks.py::test_permission_exempts_zone2_regardless_of_ceiling`.

## 6. Seed data fix: HODs need MNPI clearance to match the demo narrative

The assessment's Scenario 2 narrative says Dr. Vikram (HOD) should see the
MNPI-tagged `N-O11` (department budget) but not `N-O12` (MNPI+CONFIDENTIAL).
The original seed data gives both HOD users (`U-VIKRAM`, `U-SHARMA`) an
**empty** `compliance_clearance` — under Check 2's rule
(`compliance_tags ⊆ compliance_clearance`), an empty clearance excludes
*any* tagged node, so Vikram would see neither `N-O11` nor `N-O12`,
identical to Priya, contradicting the explicit "sees budget but not vendor
negotiation" comparison the demo script calls for.

Fixed by seeding both HODs with `compliance_clearance = {"MNPI"}` (not
`CONFIDENTIAL`) in `supabase/seed.sql` — an HOD is expected to see their own
department's confidential strategic decisions, but the deeper
`MNPI+CONFIDENTIAL` tier stays ADMIN-only. This is a data change, not a
logic change: Check 2's rule was already correct and is unchanged.

## 7. Multi-parent DAG handling

A node like "Post-TKR Protocol Area" (`HL-08-POST-TKR`) has
`parent_ids = [HL-05-ORTHO, HL-05-SURG]`. `bfs_traversal.py` uses a FIFO
queue plus a `visited: dict[id, distance]` map shared across both the
downward and upward passes (§2), so a multi-parent/multi-child node is
processed exactly once regardless of which parent or path reaches it first
— see
`tests/test_bfs.py::test_multi_parent_node_reaches_both_ancestor_departments_exactly_once`
and `test_dept_level_entry_reaches_sub_specialty_descendants_but_not_sibling_dept`.

The permission ceiling that applies to a node's own record is always the
node's own `hierarchy_level_id → level_number`, independent of which
path BFS used to reach it.

## 8. Round trips, and the GAP 5 tradeoff actually made

The pipeline makes exactly **2 sequential network round trips** to
Supabase: (1) the user row and `hierarchy_levels`, fetched concurrently
since BFS needs both before it can run; (2) one `knowledge_nodes` query
already scoped by SQL to `hierarchy_level_id IN (BFS ∪ Zone2) AND org_id = ?`
— i.e. SQL enforces structural BFS/Zone2 scope and Check 1 (isolation)
before any content is fetched. Checks 2-5 (compliance, permission,
temporal, derivability) then run in-process, sequentially, against that
already-scoped result set.

This is a deliberate, measured tradeoff, not an oversight. An earlier
version deferred *all* content fetch until after all 5 checks, using a
content-free metadata-only query (id, tags, status, valid_until,
derivability_score — never title/content) followed by a separate final
content fetch: 3 round trips, strictly more GAP-5-conservative. Timing each
Supabase call in isolation against this project showed **~200-300ms of pure
network latency per round trip regardless of query complexity** — so 3
round trips cost 900ms-1.5s wall clock, over the assessment's 500ms budget,
while 2 round trips lands at or under it. The assessment's own FAQ
explicitly sanctions this choice: *"application-level filtering is faster
to build... acknowledge the tradeoff and explain how you'd move to RLS in
production."*

**What the tradeoff actually costs**: content (title/content) for nodes
that fail Checks 2-5 does cross the DB→backend network boundary before
being filtered out — it is never serialized into the API response, but it
did leave the database, which a maximally strict GAP-5 reading would avoid.
**What it does not cost**: nodes outside the BFS+Zone2 structural scope, or
outside the user's `org_id`, are never fetched at all — the boundary that
matters most (department isolation, multi-tenant isolation) is still
enforced entirely in SQL, before any query executes in the backend.

In production this tradeoff should be revisited in favor of real RLS
policies evaluated inside Postgres (same predicates: `org_id = current_org()`,
`compliance_tags <@ current_clearance()`, `hierarchy_level_id = ANY(reachable)`,
etc.) — RLS removes the network hop entirely for the filtering decision, so
there is no latency-vs-strictness tradeoff to make in the first place, and
it also protects against a client bypassing this API and querying Supabase
directly.

## 9. Cycle prevention

The shared `visited` set in `bfs_traversal.py` makes both the downward and
upward passes loop-safe by construction — a level id already in `visited`
is never re-enqueued, so an accidental cycle (`A → B → A`) terminates
instead of looping forever
(`tests/test_bfs.py::test_visited_set_prevents_infinite_loop_on_accidental_cycle`).

This assessment does not add insert-time DFS cycle validation on
`hierarchy_levels.parent_ids` writes (out of scope given the static-graph
constraint), but the fix is well-understood: before accepting a new/updated
`parent_ids` entry, run a DFS from the proposed parent and reject the write
if it can reach back to the child being edited.

## 10. Derivability scoring

`derivability_score` is a precomputed column (seeded in `supabase/seed.sql`),
never computed at query time — Check 5 is a single `< threshold` comparison,
identical in shape to the other four checks. The seed data encodes the
distinction the assessment calls out directly: "Standard dose of Paracetamol
is 500-1000mg" (`N-D02`, score 0.95, generic/derivable) vs. "Supra Ortho uses
Paracetamol 650mg QDS as first-line post-TKR pain" (`N-O02`, score 0.08,
organization-specific decision) — same drug, wildly different derivability,
because one is textbook knowledge and the other is a documented local
decision with an owner and a date.

## 11. Deviation from the spec's literal schema: dropped a UNIQUE constraint

The assessment's schema SQL includes `UNIQUE(org_id, level_number, department)`
on `hierarchy_levels`. The assessment's own seed data violates this: level 8
department `ortho` has three legitimate sibling nodes (`HL-08-ORTHO-GEN`,
`HL-08-ORTHO-TKR`, and the multi-parent `HL-08-POST-TKR`). A DAG can have
arbitrarily many distinct nodes at the same level within the same department
— `id` is already the real identity/primary key, so this extra constraint
was redundant and actively wrong for the intended graph shape. Removed it in
`supabase/schema.sql` rather than distort the seed data to fit an incorrect
constraint.

## 12. Illustrative numbers vs. actual measured output

The assessment's Expected Pipeline Results table gives approximate targets
(Priya ~15, Vikram ~22, Suresh ~40) and its FAQ explicitly says these
"describe the production system... your demo shows the same PATTERN at
smaller scale," not an exact contract. Measured against the live seed data
with all fixes above applied: **Priya 13, Vikram 22, Suresh 42** — correct
ordering, correct department isolation (Priya/Vikram see only `ortho`;
Suresh sees all departments), zero MNPI/superseded/high-derivability leakage,
all in well under 500ms end-to-end.

## 13. Known limitations / production next steps

- Application-level filtering, not RLS (see §8) — acceptable for a demo,
  not for production multi-tenant access.
- No real-time graph mutation handling; `hierarchy_levels` is treated as
  static per the assessment's scope.
- No insert-time cycle validation (traversal-time protection only, see §9).
- Entry-point fallback to the org root for departments with no dedicated DAG
  branch (e.g. a Pharmacist before a Pharmacy hierarchy exists) means such a
  user's candidate set is driven almost entirely by Zone 2 nodes — a
  reasonable default, but worth flagging explicitly when onboarding a new
  department in production.
