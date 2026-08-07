from __future__ import annotations

from types import SimpleNamespace

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.workspaces.repository import WorkspaceRepository


class _FakeScalarList:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None


class _FakeExecuteResult:
    def __init__(self, *, one=None, many=None):
        self._one = one
        self._many = many or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return _FakeScalarList(self._many)


class _FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, statement):
        return self._responses.pop(0)


def _user(*, active_workspace=None, active_restaurant_id=None):
    return SimpleNamespace(active_workspace=active_workspace, active_restaurant_id=active_restaurant_id)


async def test_prefers_active_workspace_when_it_is_merchant():
    user = _user(
        active_workspace=SimpleNamespace(workspace_type="merchant", primary_restaurant_id=7),
        active_restaurant_id=99,  # would resolve to a different restaurant if used — must not be reached
    )
    session = _FakeSession([_FakeExecuteResult(one=user)])
    repo = WorkspaceRepository(session)

    result = await repo.get_active_merchant_restaurant_id(1)

    assert result == 7


async def test_falls_back_to_active_restaurant_id_when_workspace_is_customer():
    """Reproduces the real bug: a merchant application was approved (so the
    user has a RestaurantUserAssignment and active_restaurant_id is set),
    but active_workspace_id is still pinned at the customer workspace
    created for every user at signup."""
    user = _user(
        active_workspace=SimpleNamespace(workspace_type="customer", primary_restaurant_id=None),
        active_restaurant_id=7,
    )
    session = _FakeSession(
        [
            _FakeExecuteResult(one=user),
            _FakeExecuteResult(many=[SimpleNamespace(id=1)]),  # RestaurantUserAssignment exists
        ]
    )
    repo = WorkspaceRepository(session)

    result = await repo.get_active_merchant_restaurant_id(1)

    assert result == 7


async def test_fallback_rejects_restaurant_with_no_assignment():
    """A stale/tampered active_restaurant_id must not grant access to a
    restaurant the user has no real relationship with."""
    user = _user(
        active_workspace=SimpleNamespace(workspace_type="customer", primary_restaurant_id=None),
        active_restaurant_id=7,
    )
    session = _FakeSession(
        [
            _FakeExecuteResult(one=user),
            _FakeExecuteResult(many=[]),  # no RestaurantUserAssignment for restaurant 7
        ]
    )
    repo = WorkspaceRepository(session)

    result = await repo.get_active_merchant_restaurant_id(1)

    assert result is None


async def test_returns_none_when_no_active_restaurant_and_not_merchant():
    user = _user(
        active_workspace=SimpleNamespace(workspace_type="customer", primary_restaurant_id=None),
        active_restaurant_id=None,
    )
    session = _FakeSession([_FakeExecuteResult(one=user)])
    repo = WorkspaceRepository(session)

    result = await repo.get_active_merchant_restaurant_id(1)

    assert result is None


async def test_returns_none_when_user_missing():
    session = _FakeSession([_FakeExecuteResult(one=None)])
    repo = WorkspaceRepository(session)

    result = await repo.get_active_merchant_restaurant_id(999)

    assert result is None
