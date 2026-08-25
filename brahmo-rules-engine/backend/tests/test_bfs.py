from models.node import HierarchyLevel
from pipeline.bfs_traversal import bfs_reachable
from pipeline.entry_point_resolver import resolve_entry_point
from pipeline.zone2_injector import inject_zone2

HIERARCHY = [
    HierarchyLevel(id="HL-01", org_id="supra", level_number=1, level_name="Hospital", department=None, parent_ids=[], zone=1),
    HierarchyLevel(id="HL-03-CLIN", org_id="supra", level_number=3, level_name="Clinical Division", department=None, parent_ids=["HL-01"], zone=1),
    HierarchyLevel(id="HL-05-ORTHO", org_id="supra", level_number=5, level_name="Orthopaedics Dept", department="ortho", parent_ids=["HL-03-CLIN"], zone=1),
    HierarchyLevel(id="HL-05-SURG", org_id="supra", level_number=5, level_name="Surgery Dept", department="surgery", parent_ids=["HL-03-CLIN"], zone=1),
    HierarchyLevel(id="HL-08-ORTHO-GEN", org_id="supra", level_number=8, level_name="Ortho General", department="ortho", parent_ids=["HL-05-ORTHO"], zone=1),
    HierarchyLevel(id="HL-08-POST-TKR", org_id="supra", level_number=8, level_name="Post-TKR Protocol Area", department="ortho", parent_ids=["HL-05-ORTHO", "HL-05-SURG"], zone=1),
    HierarchyLevel(id="HL-10-ORTHO-W", org_id="supra", level_number=10, level_name="Ortho Ward", department="ortho", parent_ids=["HL-08-ORTHO-GEN"], zone=1),
    HierarchyLevel(id="HL-12-PATIENT", org_id="supra", level_number=12, level_name="Patient: Test", department="ortho", parent_ids=["HL-10-ORTHO-W"], zone=1),
    HierarchyLevel(id="HL-GLOBAL", org_id="supra", level_number=3, level_name="Global Constraints", department=None, parent_ids=["HL-01"], zone=2),
]


def test_bfs_walks_upward_from_ward_to_hospital_and_down_to_own_patient():
    reachable = bfs_reachable(HIERARCHY, "HL-10-ORTHO-W")
    assert reachable["HL-10-ORTHO-W"] == 0
    assert reachable["HL-08-ORTHO-GEN"] == 1
    assert reachable["HL-05-ORTHO"] == 2
    assert reachable["HL-03-CLIN"] == 3
    assert reachable["HL-01"] == 4
    # Own descendant (her patient) is reachable — downward from entry
    assert reachable["HL-12-PATIENT"] == 1
    # Cardiology/Surgery are not on this path at all
    assert "HL-05-SURG" not in reachable
    # Sub-specialty sibling (child of the ancestor OrthoDept, not of Ward
    # itself) is NOT reachable — a ward-level nurse isn't stationed there.
    assert "HL-08-POST-TKR" not in reachable


def test_dept_level_entry_reaches_sub_specialty_descendants_but_not_sibling_dept():
    # Dr. Vikram enters at the DEPARTMENT level, above the ward — his
    # downward subtree includes the TKR unit, the multi-parent Post-TKR
    # node, the ward, AND its patient. He must NOT gain Surgery (a
    # sibling department under Clinical Division, not a descendant of
    # Orthopaedics).
    reachable = bfs_reachable(HIERARCHY, "HL-05-ORTHO")
    assert reachable["HL-05-ORTHO"] == 0
    assert "HL-08-ORTHO-GEN" in reachable
    assert "HL-08-POST-TKR" in reachable  # multi-parent descendant, reached downward
    assert "HL-10-ORTHO-W" in reachable
    assert "HL-12-PATIENT" in reachable
    assert reachable["HL-03-CLIN"] == 1  # ancestor, upward
    assert reachable["HL-01"] == 2
    assert "HL-05-SURG" not in reachable  # sibling dept — isolation preserved


def test_root_entry_reaches_the_entire_graph():
    # Admin Suresh enters at the Hospital root, which has no parents at
    # all — reaching "everything" is only possible via the downward pass.
    reachable = bfs_reachable(HIERARCHY, "HL-01")
    assert set(reachable.keys()) == {h.id for h in HIERARCHY}


def test_multi_parent_node_reaches_both_ancestor_departments_exactly_once():
    # HL-08-POST-TKR has TWO parents: HL-05-ORTHO and HL-05-SURG. A user
    # entering the DAG at this node must reach BOTH departments walking
    # up, each exactly once (visited set), not miss one or loop forever.
    reachable = bfs_reachable(HIERARCHY, "HL-08-POST-TKR")
    assert reachable["HL-08-POST-TKR"] == 0
    assert reachable["HL-05-ORTHO"] == 1
    assert reachable["HL-05-SURG"] == 1
    # Both parents converge on the same ancestor (HL-03-CLIN) — must be
    # visited once, at the shortest distance, not processed twice.
    assert reachable["HL-03-CLIN"] == 2
    assert reachable["HL-01"] == 3
    assert len(reachable) == 5  # no duplicate/ghost entries from double-processing


def test_visited_set_prevents_infinite_loop_on_accidental_cycle():
    cyclic = HIERARCHY + [
        HierarchyLevel(id="HL-CYCLE-A", org_id="supra", level_number=9, level_name="A", parent_ids=["HL-CYCLE-B"], zone=1),
        HierarchyLevel(id="HL-CYCLE-B", org_id="supra", level_number=9, level_name="B", parent_ids=["HL-CYCLE-A"], zone=1),
    ]
    # Must terminate (would hang forever without a visited set)
    reachable = bfs_reachable(cyclic, "HL-CYCLE-A")
    assert reachable["HL-CYCLE-A"] == 0
    assert reachable["HL-CYCLE-B"] == 1


def test_zone2_injection_adds_global_nodes_not_structurally_reachable():
    bfs_only = bfs_reachable(HIERARCHY, "HL-10-ORTHO-W")
    assert "HL-GLOBAL" not in bfs_only  # sibling of Clinical Division, not an ancestor

    merged = inject_zone2(HIERARCHY, bfs_only)
    assert "HL-GLOBAL" in merged
    # HL-GLOBAL's parent HL-01 was reached at distance 4 -> inherits that distance
    assert merged["HL-GLOBAL"] == merged["HL-01"]


def test_entry_point_resolver_viewer_ceiling_picks_ward_not_department():
    # High (restrictive) ceiling, VIEWER-like -> most senior permitted
    # position in "ortho" is the ward (level 10), matching Nurse Priya.
    entry = resolve_entry_point(HIERARCHY, "ortho", ceiling_level=10)
    assert entry.id == "HL-10-ORTHO-W"


def test_entry_point_resolver_hod_ceiling_picks_department_level():
    # Low (permissive) ceiling, HOD-like -> most senior permitted position
    # in "ortho" is the department itself (level 5), matching Dr. Vikram —
    # NOT the ward, even though the ward is also in "ortho" and reachable.
    entry = resolve_entry_point(HIERARCHY, "ortho", ceiling_level=4)
    assert entry.id == "HL-05-ORTHO"


def test_entry_point_resolver_falls_back_to_root_for_unknown_department():
    entry = resolve_entry_point(HIERARCHY, "pharmacy", ceiling_level=12)
    assert entry.id == "HL-01"
