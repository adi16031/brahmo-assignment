from typing import Optional

from pydantic import BaseModel


class User(BaseModel):
    id: str
    org_id: str
    name: str
    role: str  # ADMIN | HOD | EDITOR | VIEWER | QUALITY | AUDITOR (or any future role)
    department: str
    ceiling_level: int
    write_ceiling: Optional[int] = None
    compliance_clearance: list[str] = []
    status: str = "ACTIVE"


class PermissionEntry(BaseModel):
    can_read: bool
    can_write: bool


# {level_number: PermissionEntry} — compiled once per session, O(1) lookup thereafter.
PermissionMap = dict[int, PermissionEntry]
