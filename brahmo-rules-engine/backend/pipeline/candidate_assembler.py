"""
Candidate Set Assembler — Stage 6.

Annotates surviving nodes with the metadata contract the (out-of-scope)
downstream Composition Agent expects: distance_from_entry (from BFS/Zone2
merge), compression_hint (derived from distance), and pass-through fields.
"""

from models.node import CandidateNode, KnowledgeNode


def compression_hint_for_distance(distance: int) -> str:
    if distance <= 1:
        return "FULL"
    if distance == 2:
        return "COMPRESSED"
    return "CONSTRAINT_ONLY"


def assemble_candidate_set(
    nodes: list[KnowledgeNode],
    distances_by_hierarchy_level: dict[str, int],
    hierarchy_level_numbers: dict[str, int],
) -> list[CandidateNode]:
    candidates: list[CandidateNode] = []
    for node in nodes:
        distance = distances_by_hierarchy_level.get(node.hierarchy_level_id, 0)
        level_number = hierarchy_level_numbers.get(node.hierarchy_level_id, 0)
        candidates.append(
            CandidateNode(
                id=node.id,
                type=node.type,
                title=node.title,
                content=node.content,
                importance=node.importance,
                zone=node.zone,
                hierarchy_level=level_number,
                department=node.department,
                distance_from_entry=distance,
                compression_hint=compression_hint_for_distance(distance),
            )
        )
    # Most important / closest-to-entry first — makes the demo table read naturally.
    candidates.sort(key=lambda c: (c.distance_from_entry, -c.importance))
    return candidates
