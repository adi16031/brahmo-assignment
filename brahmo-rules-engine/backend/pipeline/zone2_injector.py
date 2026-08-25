"""
Zone 2 Injector — Stage 4.

Injects all hierarchy levels tagged zone=2 (GLOBAL) into the reachable
set produced by BFS, regardless of whether the user's traversal path
structurally reaches them. Zone 2 nodes are NOT exempt from the 5-check
filter — they still must pass isolation/compliance/permission/temporal/
derivability like everything else (see demo Scenario 4: some Zone 2
nodes could in principle be MNPI-tagged or above a user's ceiling).

distance_from_entry for an injected Zone 2 level is derived from its
nearest already-visited parent (Zone 2 levels have real parent_ids too,
e.g. HL-GLOBAL's parent is HL-01) — if that parent was reached during
BFS, the injected node inherits that parent's distance (this matches the
worked example in the setup guide, where a Zone-2 node and the Hospital
root it hangs off both show the same distance_from_entry). If no parent
was reached, it falls back to (max BFS distance + 1) as a sentinel,
signalling "reached only via injection, not via structural traversal".
"""

from models.node import HierarchyLevel


def inject_zone2(
    hierarchy_levels: list[HierarchyLevel], reachable: dict[str, int]
) -> dict[str, int]:
    merged = dict(reachable)
    by_id = {h.id: h for h in hierarchy_levels}
    fallback_distance = (max(reachable.values()) + 1) if reachable else 0

    for level in hierarchy_levels:
        if level.zone != 2 or level.id in merged:
            continue
        parent_distances = [
            merged[p] for p in level.parent_ids if p in merged
        ]
        merged[level.id] = min(parent_distances) if parent_distances else fallback_distance

    return merged
