from typing import Optional

from pydantic import BaseModel


class HierarchyLevel(BaseModel):
    id: str
    org_id: str
    level_number: int
    level_name: str
    department: Optional[str] = None
    parent_ids: list[str] = []
    zone: int = 1


class KnowledgeNode(BaseModel):
    id: str
    org_id: str
    hierarchy_level_id: str
    type: str  # CONSTRAINT | DECISION | ANTI_PATTERN | FACT
    title: str
    content: str
    importance: float
    zone: int
    status: str
    derivability_score: float
    compliance_tags: list[str] = []
    valid_until: Optional[str] = None
    superseded_by: Optional[str] = None
    department: Optional[str] = None


class CandidateNode(BaseModel):
    id: str
    type: str
    title: str
    content: str
    importance: float
    zone: int
    hierarchy_level: int
    department: Optional[str] = None
    distance_from_entry: int
    compression_hint: str  # FULL | COMPRESSED | CONSTRAINT_ONLY
