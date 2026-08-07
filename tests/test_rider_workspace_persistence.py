from __future__ import annotations

from types import SimpleNamespace

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.workspaces.service import WorkspaceService


def _user(*, roles):
    return SimpleNamespace(roles=roles)


def _role(code):
    return SimpleNamespace(role=SimpleNamespace(code=code))


async def test_ensure_rider_workspace_skips_users_without_rider_role():
    service = WorkspaceService.__new__(WorkspaceService)
    service.repository = SimpleNamespace()  # unused — should return before touching it
    user = _user(roles=[_role("customer")])

    result = await service.ensure_rider_workspace_if_eligible(user)

    assert result is None


async def test_ensure_rider_workspace_creates_for_rider_role():
    created = SimpleNamespace(id=42, workspace_type="rider")

    async def fake_get_or_create(u):
        assert u is user
        return created

    service = WorkspaceService.__new__(WorkspaceService)
    service.repository = SimpleNamespace(get_or_create_rider_workspace=fake_get_or_create)
    user = _user(roles=[_role("customer"), _role("rider")])

    result = await service.ensure_rider_workspace_if_eligible(user)

    assert result is created
