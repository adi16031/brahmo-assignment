"""
Entry Point Resolver — Stage 2.

Maps a user to their DAG leaf node (their BFS starting position) using
BOTH their department AND their ceiling_level — department alone is
ambiguous, because a department can have nodes at several levels (e.g.
"ortho" has department-level, sub-specialty, ward, AND patient-record
nodes at levels 5/8/10/12).

Rule: among the department's nodes, take the SHALLOWEST one (smallest
level_number, i.e. most senior/broadest) that the user's ceiling still
permits them to read (level_number >= ceiling_level) — this reuses the
exact same ceiling semantics as Check 3, so a user's entry point is
"the most senior position in their own department they're allowed to
occupy." A VIEWER with a high (restrictive) ceiling bottoms out at the
ward; an HOD with a low (permissive) ceiling enters at the department
level itself. Worked examples from the assessment:

    Nurse Priya  (ortho, ceiling 10) -> nodes with level >= 10: {Ward(10), Patient(12)}
                                         -> shallowest: Ward (10)      ✓
    Dr. Vikram   (ortho, ceiling  4) -> nodes with level >= 4: {5,8,8,8,10,12}
                                         -> shallowest: Dept (5)       ✓

If the user's ceiling is stricter than every node in their department
(no node has level_number >= ceiling), fall back to the deepest node
available in that department (their closest achievable position).

If the department has no hierarchy_levels rows at all (e.g. a Pharmacist
whose department has no dedicated DAG branch yet), fall back to the org
root (level_number == 1). BFS from the root only reaches the root itself
(no parents to walk up to), so such a user's candidate set is driven
almost entirely by Zone 2 (global) nodes — a defensible default: no
dept-specific knowledge exists yet, but hospital-wide safety constraints
still apply.
"""

from models.node import HierarchyLevel


def resolve_entry_point(
    hierarchy_levels: list[HierarchyLevel], department: str, ceiling_level: int
) -> HierarchyLevel:
    dept_matches = [h for h in hierarchy_levels if h.department == department]

    if dept_matches:
        eligible = [h for h in dept_matches if h.level_number >= ceiling_level]
        if eligible:
            return min(eligible, key=lambda h: h.level_number)
        return max(dept_matches, key=lambda h: h.level_number)

    root_candidates = [h for h in hierarchy_levels if h.level_number == min(
        (x.level_number for x in hierarchy_levels), default=1
    )]
    if not root_candidates:
        raise ValueError("hierarchy_levels is empty — cannot resolve an entry point")
    return root_candidates[0]
