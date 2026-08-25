"""
End-to-end integration test — runs against a REAL Supabase project with
schema.sql + seed.sql already loaded. Skipped automatically if
SUPABASE_URL / SUPABASE_SERVICE_KEY are not set (e.g. before you've
filled in .env.local), so `pytest` stays green out of the box.

Once your Supabase project is live, run:
    cd backend && pytest tests/test_pipeline.py -v
"""

import pytest

from config import DEFAULT_ORG_ID, SUPABASE_SERVICE_KEY, SUPABASE_URL, get_supabase
from pipeline.orchestrator import run_pipeline

pytestmark = pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL / SUPABASE_SERVICE_KEY not set — fill in .env.local to run this suite",
)


@pytest.fixture(scope="module")
def supabase():
    return get_supabase()


def test_priya_sees_only_ortho_and_global_nodes(supabase):
    result = run_pipeline(supabase, "U-PRIYA", DEFAULT_ORG_ID)
    assert 10 <= result.funnel.after_check5 <= 20  # ~15 expected

    depts = {c.department for c in result.candidate_set}
    assert depts.issubset({"ortho", None})  # None = Zone 2 global nodes

    ids = {c.id for c in result.candidate_set}
    assert "N-O11" not in ids  # MNPI, no clearance
    assert "N-O12" not in ids  # MNPI + CONFIDENTIAL
    assert "N-D01" not in ids  # high derivability
    assert "N-M08" not in ids  # superseded (also out of BFS reach)


def test_vikram_sees_more_than_priya_same_pipeline(supabase):
    priya = run_pipeline(supabase, "U-PRIYA", DEFAULT_ORG_ID)
    vikram = run_pipeline(supabase, "U-VIKRAM", DEFAULT_ORG_ID)
    assert vikram.funnel.after_check5 > priya.funnel.after_check5

    vikram_ids = {c.id for c in vikram.candidate_set}
    assert "N-O11" in vikram_ids       # HOD-level budget doc, no compliance tag beyond MNPI clearance gap
    assert "N-O12" not in vikram_ids   # needs ADMIN-level (MNPI+CONFIDENTIAL) clearance


def test_suresh_sees_nearly_everything(supabase):
    result = run_pipeline(supabase, "U-SURESH", DEFAULT_ORG_ID)
    assert result.funnel.after_bfs == result.funnel.total_nodes  # enters at root, sees all
    ids = {c.id for c in result.candidate_set}
    assert "N-A01" in ids
    assert "N-C04" in ids


def test_zone2_toggle_removes_global_safety_nodes(supabase):
    with_zone2 = run_pipeline(supabase, "U-PRIYA", DEFAULT_ORG_ID, zone2_enabled=True)
    without_zone2 = run_pipeline(supabase, "U-PRIYA", DEFAULT_ORG_ID, zone2_enabled=False)
    with_ids = {c.id for c in with_zone2.candidate_set}
    without_ids = {c.id for c in without_zone2.candidate_set}
    assert "N-G01" in with_ids  # Warfarin-NSAID global constraint present
    assert "N-G01" not in without_ids


def test_pipeline_runs_under_500ms(supabase):
    result = run_pipeline(supabase, "U-PRIYA", DEFAULT_ORG_ID)
    assert result.pipeline_timing.total_ms < 500
