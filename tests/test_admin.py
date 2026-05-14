from sqlalchemy import select

from marketplace_parse.db.enums import UserRole
from marketplace_parse.db.models import RoleChangeAudit
from marketplace_parse.db.session import async_session_maker


async def test_list_users_unauth_401(client):
    resp = await client.get("/api/admin/users")
    assert resp.status_code == 401


async def test_list_users_as_regular_user_403(user_client):
    resp = await user_client.get("/api/admin/users")
    assert resp.status_code == 403


async def test_list_users_as_admin(admin_client, user_client):
    resp = await admin_client.get("/api/admin/users")
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert "admin@example.com" in emails
    assert "user@example.com" in emails


async def test_promote_user_writes_audit(admin_client, user_client):
    listing = await admin_client.get("/api/admin/users")
    target = next(u for u in listing.json() if u["email"] == "user@example.com")

    resp = await admin_client.patch(
        f"/api/admin/users/{target['user_id']}/role",
        json={"role": "analyst"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "analyst"

    async with async_session_maker() as session:
        audit = await session.scalar(
            select(RoleChangeAudit).where(
                RoleChangeAudit.target_user_id == target["user_id"]
            )
        )
        assert audit is not None
        assert audit.old_role == UserRole.user
        assert audit.new_role == UserRole.analyst


async def test_role_change_to_same_role_no_audit(admin_client, user_client):
    listing = await admin_client.get("/api/admin/users")
    target = next(u for u in listing.json() if u["email"] == "user@example.com")

    resp = await admin_client.patch(
        f"/api/admin/users/{target['user_id']}/role",
        json={"role": "user"},
    )
    assert resp.status_code == 200

    async with async_session_maker() as session:
        audit = await session.scalar(
            select(RoleChangeAudit).where(
                RoleChangeAudit.target_user_id == target["user_id"]
            )
        )
        assert audit is None


async def test_admin_cannot_change_own_role(admin_client):
    me = await admin_client.get("/api/me")
    own_id = me.json()["user_id"]
    resp = await admin_client.patch(
        f"/api/admin/users/{own_id}/role",
        json={"role": "user"},
    )
    assert resp.status_code == 400


async def test_change_role_unknown_user_404(admin_client):
    resp = await admin_client.patch(
        "/api/admin/users/99999/role", json={"role": "analyst"}
    )
    assert resp.status_code == 404


async def test_delete_user_as_admin(admin_client, user_client):
    listing = await admin_client.get("/api/admin/users")
    target = next(u for u in listing.json() if u["email"] == "user@example.com")

    resp = await admin_client.delete(f"/api/admin/users/{target['user_id']}")
    assert resp.status_code == 204

    after = await admin_client.get("/api/admin/users")
    emails = {u["email"] for u in after.json()}
    assert "user@example.com" not in emails


async def test_admin_cannot_delete_self(admin_client):
    me = await admin_client.get("/api/me")
    own_id = me.json()["user_id"]
    resp = await admin_client.delete(f"/api/admin/users/{own_id}")
    assert resp.status_code == 400


async def test_delete_unknown_user_404(admin_client):
    resp = await admin_client.delete("/api/admin/users/99999")
    assert resp.status_code == 404


async def test_delete_user_requires_admin(user_client, other_user_client):
    me = await other_user_client.get("/api/me")
    other_id = me.json()["user_id"]
    resp = await user_client.delete(f"/api/admin/users/{other_id}")
    assert resp.status_code == 403


async def test_delete_user_with_audit_history(admin_client, user_client):
    """Regression: role_change_audit FKs lack ON DELETE CASCADE; admin
    handler nukes audit rows manually before user delete."""
    listing = await admin_client.get("/api/admin/users")
    target = next(u for u in listing.json() if u["email"] == "user@example.com")

    promote = await admin_client.patch(
        f"/api/admin/users/{target['user_id']}/role", json={"role": "analyst"}
    )
    assert promote.status_code == 200

    delete = await admin_client.delete(f"/api/admin/users/{target['user_id']}")
    assert delete.status_code == 204

    async with async_session_maker() as session:
        audit = await session.scalar(
            select(RoleChangeAudit).where(
                RoleChangeAudit.target_user_id == target["user_id"]
            )
        )
        assert audit is None
