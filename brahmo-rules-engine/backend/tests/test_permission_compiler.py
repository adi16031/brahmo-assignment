from models.user import User
from pipeline.permission_compiler import can_read_level, compile_permissions


def make_user(**overrides) -> User:
    base = dict(
        id="U-TEST", org_id="supra", name="Test", role="VIEWER",
        department="ortho", ceiling_level=10, write_ceiling=None,
        compliance_clearance=[],
    )
    base.update(overrides)
    return User(**base)


def test_viewer_can_read_at_and_below_ceiling_cannot_write():
    user = make_user(role="VIEWER", ceiling_level=10, write_ceiling=None)
    perms = compile_permissions(user)
    assert can_read_level(perms, 10) is True
    assert can_read_level(perms, 15) is True
    assert can_read_level(perms, 9) is False
    assert all(not p.can_write for p in perms.values())


def test_editor_can_write_at_and_below_write_ceiling():
    user = make_user(role="EDITOR", ceiling_level=8, write_ceiling=8)
    perms = compile_permissions(user)
    assert perms[8].can_write is True
    assert perms[7].can_write is False


def test_hod_permissive_ceiling_reads_more_than_viewer():
    hod = make_user(role="HOD", ceiling_level=4, write_ceiling=4)
    viewer = make_user(role="VIEWER", ceiling_level=10, write_ceiling=None)
    hod_perms = compile_permissions(hod)
    viewer_perms = compile_permissions(viewer)
    # Level 5 (department-level node): HOD can read it, Priya-like viewer cannot
    assert hod_perms[5].can_read is True
    assert viewer_perms[5].can_read is False


def test_admin_reads_and_writes_everything():
    admin = make_user(role="ADMIN", ceiling_level=1, write_ceiling=1)
    perms = compile_permissions(admin)
    assert all(p.can_read and p.can_write for p in perms.values())


def test_unseen_role_works_without_code_changes():
    # Simulates the "surprise test" — a role never seen during development.
    pharmacist = make_user(role="PHARMACIST", ceiling_level=12, write_ceiling=None)
    perms = compile_permissions(pharmacist)
    assert can_read_level(perms, 12) is True
    assert can_read_level(perms, 11) is False
    assert all(not p.can_write for p in perms.values())
