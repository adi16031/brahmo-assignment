"""
BFS Traversal — Stage 3.

Reachability from a user's entry point = the entry's ANCESTORS (walking
UP via parent_ids, as the assessment's flow diagram describes) UNION the
entry's own DESCENDANT SUBTREE (walking DOWN via the reverse edges).

Why both directions are required (not just "up", despite the flow diagram
only narrating the upward walk): the assessment's own expected results
require Admin Suresh, entering at the Hospital root (level 1, which has
NO parents), to reach all 50 nodes. A root node can only reach everything
by walking down; pure upward-only traversal from a parentless root reaches
nothing but itself. The same two-directional rule is what lets an HOD
entering at the DEPARTMENT level (e.g. Dr. Vikram at Orthopaedics) reach
sub-specialty units and the multi-parent "Post-TKR Protocol Area" node
underneath their department — exactly the multi-parent scenario the flow
diagram calls out — while a WARD-level nurse (entering deeper, below those
sub-specialty siblings) does not.

CRITICAL — the two directions must stay independent and never cross-seed
each other, or department isolation breaks:
  - The DOWNWARD pass is seeded only by the entry node and continues
    downward from whatever it finds (descendants of descendants, etc.).
    It must never also walk upward from a discovered descendant — e.g.
    Post-TKR has a SECOND parent (Surgery); if reaching Post-TKR while
    exploring downward from Vikram's Orthopaedics entry triggered an
    upward walk too, he would leak into the Surgery department.
  - The UPWARD pass is seeded only by the entry node and continues
    upward from whatever it finds (ancestors of ancestors, etc.). It must
    never also walk downward from a discovered ancestor — e.g. Clinical
    Division is an ancestor of Ward; if reaching it triggered a downward
    walk, a Ward-level nurse would gain every other department under
    Clinical Division (Cardiology, Medicine, ...).

Both passes share one `visited` dict (a node cannot be its own ancestor
AND descendant in a DAG, so there's no real conflict) and use a FIFO
queue, so multi-parent/multi-child nodes are processed exactly once and
an accidental cycle cannot cause an infinite loop.
"""

from collections import deque

from models.node import HierarchyLevel


def bfs_reachable(
    hierarchy_levels: list[HierarchyLevel], entry_id: str
) -> dict[str, int]:
    by_id = {h.id: h for h in hierarchy_levels}
    if entry_id not in by_id:
        raise ValueError(f"Unknown entry point hierarchy_level id: {entry_id}")

    children_by_parent: dict[str, list[str]] = {}
    for h in hierarchy_levels:
        for parent_id in h.parent_ids:
            children_by_parent.setdefault(parent_id, []).append(h.id)

    visited: dict[str, int] = {entry_id: 0}

    # Downward: entry's own descendant subtree.
    queue: deque[str] = deque([entry_id])
    while queue:
        current_id = queue.popleft()
        for child_id in children_by_parent.get(current_id, []):
            if child_id in visited or child_id not in by_id:
                continue
            visited[child_id] = visited[current_id] + 1
            queue.append(child_id)

    # Upward: entry's ancestor chain.
    queue = deque([entry_id])
    while queue:
        current_id = queue.popleft()
        current = by_id.get(current_id)
        if current is None:
            continue
        for parent_id in current.parent_ids:
            if parent_id in visited or parent_id not in by_id:
                continue
            visited[parent_id] = visited[current_id] + 1
            queue.append(parent_id)

    return visited
