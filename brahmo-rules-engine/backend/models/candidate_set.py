from typing import Optional

from pydantic import BaseModel

from .node import CandidateNode


class DagLevelView(BaseModel):
    id: str
    level_name: str
    level_number: int
    department: Optional[str] = None
    zone: int
    parent_ids: list[str]
    reachable: bool
    distance: Optional[int] = None
    reachable_via: Optional[str] = None  # "BFS" | "ZONE2" | None
    is_entry: bool = False


class PipelineTiming(BaseModel):
    permission_compile_ms: float
    entry_resolve_ms: float
    bfs_ms: float
    zone2_inject_ms: float
    fetch_nodes_ms: float
    check1_isolation_ms: float
    check2_compliance_ms: float
    check3_permission_ms: float
    check4_temporal_ms: float
    check5_derivability_ms: float
    total_ms: float


class Funnel(BaseModel):
    total_nodes: int
    after_bfs: int
    after_zone2: int
    after_check1: int
    after_check2: int
    after_check3: int
    after_check4: int
    after_check5: int


class CandidateSetResponse(BaseModel):
    user_id: str
    user_name: str
    role: str
    ceiling_level: int
    entry_point: str
    entry_point_name: Optional[str] = None
    pipeline_timing: PipelineTiming
    funnel: Funnel
    candidate_set: list[CandidateNode]
    dag: list[DagLevelView]
