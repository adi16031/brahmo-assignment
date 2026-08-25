from datetime import datetime, timedelta, timezone

from pipeline.five_check_filter import FilterableNode, run_five_checks
from pipeline.permission_compiler import compile_permissions
from models.user import User

NOW = datetime(2026, 8, 23, tzinfo=timezone.utc)


def node(**overrides) -> FilterableNode:
    base = dict(
        id="N-TEST", org_id="supra", compliance_tags=[],
        hierarchy_level_number=5, zone=1, status="ACTIVE", valid_until=None,
        derivability_score=0.1,
    )
    base.update(overrides)
    return FilterableNode(**base)


def perms(ceiling_level: int, write_ceiling=None):
    return compile_permissions(User(
        id="U-TEST", org_id="supra", name="Test", role="VIEWER",
        department="ortho", ceiling_level=ceiling_level, write_ceiling=write_ceiling,
    ))


def test_isolation_excludes_other_orgs():
    nodes = [node(id="A", org_id="supra"), node(id="B", org_id="other_hospital")]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check1"]} == {"A"}


def test_compliance_excludes_mnpi_for_uncleared_user():
    nodes = [
        node(id="clean"),
        node(id="mnpi", compliance_tags=["MNPI"]),
    ]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check2"]} == {"clean"}


def test_compliance_allows_mnpi_for_cleared_auditor():
    nodes = [node(id="mnpi", compliance_tags=["MNPI"])]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=["MNPI"], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check2"]} == {"mnpi"}


def test_permission_excludes_zone1_nodes_above_ceiling():
    nodes = [
        node(id="deep", hierarchy_level_number=10, zone=1),
        node(id="hod_level", hierarchy_level_number=4, zone=1),
    ]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(10), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check3"]} == {"deep"}


def test_permission_exempts_zone2_regardless_of_ceiling():
    # A high (restrictive) ceiling would fail a zone=1 node at this level,
    # but hospital-wide global constraints (zone=2) apply to everyone —
    # required by the assessment's Zone-2 demo scenario.
    nodes = [
        node(id="global_safety", hierarchy_level_number=3, zone=2),
        node(id="dept_content", hierarchy_level_number=3, zone=1),
    ]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(10), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check3"]} == {"global_safety"}


def test_temporal_excludes_superseded_and_expired():
    nodes = [
        node(id="active"),
        node(id="superseded", status="SUPERSEDED"),
        node(id="expired", valid_until=(NOW - timedelta(days=1)).isoformat()),
        node(id="future_valid", valid_until=(NOW + timedelta(days=1)).isoformat()),
    ]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check4"]} == {"active", "future_valid"}


def test_derivability_excludes_generic_knowledge():
    nodes = [
        node(id="org_specific", derivability_score=0.08),
        node(id="generic_fact", derivability_score=0.92),
    ]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert {n.id for n in result["after_check5"]} == {"org_specific"}


def test_checks_are_sequential_not_independent():
    # A node that fails check2 must never reach check3/4/5's input set,
    # even if it would have passed those checks individually.
    nodes = [node(id="mnpi_but_otherwise_fine", compliance_tags=["MNPI"], hierarchy_level_number=1, derivability_score=0.0)]
    result = run_five_checks(nodes, org_id="supra", compliance_clearance=[], permission_map=perms(1), derivability_threshold=0.7, now=NOW)
    assert result["after_check2"] == []
    assert result["after_check3"] == []
    assert result["after_check4"] == []
    assert result["after_check5"] == []
