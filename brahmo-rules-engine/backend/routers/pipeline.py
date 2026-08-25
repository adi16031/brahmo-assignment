from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import DEFAULT_ORG_ID, get_supabase
from models.candidate_set import CandidateSetResponse
from pipeline.orchestrator import run_pipeline

router = APIRouter()


class RunPipelineRequest(BaseModel):
    user_id: str
    org_id: str | None = None
    zone2_enabled: bool = True


@router.get("/users")
def list_users():
    supabase = get_supabase()
    resp = (
        supabase.table("users")
        .select("id, name, role, department, ceiling_level, write_ceiling, compliance_clearance")
        .eq("org_id", DEFAULT_ORG_ID)
        .order("name")
        .execute()
    )
    return resp.data


@router.post("/pipeline/run", response_model=CandidateSetResponse)
def run(req: RunPipelineRequest):
    supabase = get_supabase()
    org_id = req.org_id or DEFAULT_ORG_ID
    try:
        return run_pipeline(
            supabase, req.user_id, org_id, zone2_enabled=req.zone2_enabled
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
