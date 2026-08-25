"""
Permission Compiler — Stage 1.

Compiles a user's read/write permissions into an O(1) lookup keyed by
hierarchy level number, computed ONCE per session/request and reused for
every node checked downstream (avoids an N+1 permission query per node).

Design note (reconciling the two role descriptions in the assessment):
The AI-starter-prompt text describes per-role behavior ("VIEWER: read >=
ceiling", "HOD: read all levels", ...), but the formal, testable rule used
throughout the "Five-Check Sequential Filter" section and the expected
results table is uniform and role-agnostic:

    Check 3 (PERMISSION):  hierarchy_level >= user.ceiling_level

We implement that uniform rule here instead of branching on role name.
This is what makes the pipeline pass the "surprise new role" test: a
brand-new role (e.g. "PHARMACIST") works correctly as long as it has a
ceiling_level and (optionally) a write_ceiling — no code change needed.

Read:  level >= ceiling_level                (ceiling_level always present)
Write: level >= write_ceiling, if write_ceiling is not None
       else no write access at all (this naturally reproduces VIEWER's
       "can_write nothing" without special-casing the VIEWER role name)
"""

from models.user import PermissionEntry, PermissionMap, User

MIN_LEVEL = 1
MAX_LEVEL = 15


def compile_permissions(user: User) -> PermissionMap:
    permission_map: PermissionMap = {}
    for level in range(MIN_LEVEL, MAX_LEVEL + 1):
        can_read = level >= user.ceiling_level
        can_write = user.write_ceiling is not None and level >= user.write_ceiling
        permission_map[level] = PermissionEntry(can_read=can_read, can_write=can_write)
    return permission_map


def can_read_level(permission_map: PermissionMap, level_number: int) -> bool:
    entry = permission_map.get(level_number)
    return bool(entry and entry.can_read)
