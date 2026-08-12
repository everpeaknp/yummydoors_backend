from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import OrderService


def _rider(*, id=17, work_mode="platform", accepting=True, roles=("rider",)):
    return SimpleNamespace(
        id=id,
        rider_work_mode=work_mode,
        is_accepting_offers=accepting,
        roles=[
            SimpleNamespace(role=SimpleNamespace(code=code), restaurant_id=None)
            for code in roles
        ],
        restaurant_assignments=[],
        active_restaurant_id=None,
    )


def _order(*, id=1, restaurant_id=9, rider_user_id=None, status=OrderStatus.placed, assignment_state="open_unfilled"):
    return SimpleNamespace(
        id=id,
        restaurant_id=restaurant_id,
        rider_user_id=rider_user_id,
        status=status,
        rider_assigned_at=None,
        preparing_at=None,
        rider_assignment_state=assignment_state,
        restaurant=SimpleNamespace(
            id=restaurant_id,
            rider_dispatch_policy="ranked",
            name="Test Restaurant",
            slug="test-restaurant",
            latitude=None,
            longitude=None,
        ),
        customer_id=5,
        customer=SimpleNamespace(full_name="Test Customer"),
        order_number="ORD-TEST01",
        payment_status="unpaid",
        total_price=500.0,
        items=[],
        estimated_delivery_window=None,
        address_id=None,
        delivery_recipient_name=None,
        delivery_phone_number=None,
        delivery_address_text=None,
        delivery_latitude=None,
        delivery_longitude=None,
        rider=None,
        confirmed_at=None,
        picked_up_at=None,
        delivered_at=None,
        cancelled_at=None,
        rider_assignment_tier=None,
        rider_offer_expires_at=None,
        created_at=datetime.now(UTC),
    )


class _SelectResult:
    def __init__(self, order):
        self._order = order

    def scalars(self):
        return self

    def first(self):
        return self._order


class _UpdateResult:
    def __init__(self, rowcount):
        self.rowcount = rowcount


class _FakeSession:
    """Distinguishes the repo's eager-loaded SELECT from our conditional
    UPDATE by statement type, so we can assert the UPDATE's rowcount branch
    is actually exercised — this is what proves the compare-and-swap path
    (not just the happy path) is wired correctly."""

    def __init__(self, order, *, update_rowcount):
        self._order = order
        self._update_rowcount = update_rowcount
        self.committed = False
        self.rolled_back = False
        self.executed_update = None

    async def execute(self, stmt):
        if getattr(stmt, "is_update", False):
            self.executed_update = stmt
            return _UpdateResult(self._update_rowcount)
        return _SelectResult(self._order)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def get(self, model, id):
        return None


class _FakeDispatchService:
    async def get_pending_offer_for_rider(self, *, rider_user_id, order_id):
        return None


@pytest.mark.asyncio
async def test_rider_claim_conflict_when_concurrently_claimed(monkeypatch):
    """Simulates the race: by the time our conditional UPDATE runs, another
    rider already claimed the order first (rowcount == 0 because
    rider_user_id is no longer NULL). This must surface as a 409, not a
    silent double-assignment."""
    order = _order()
    session = _FakeSession(order, update_rowcount=0)
    service = OrderService(session)

    monkeypatch.setattr(service, "_load_user_with_roles", lambda rider_user_id: _rider())
    monkeypatch.setattr(
        "app.modules.orders.service.RiderDispatchService",
        lambda session: _FakeDispatchService(),
    )

    async def fake_load_user(rider_user_id):
        return _rider()

    monkeypatch.setattr(service, "_load_user_with_roles", fake_load_user)

    with pytest.raises(HTTPException) as exc_info:
        await service.rider_claim_order(rider_user_id=17, order_id=1)

    assert exc_info.value.status_code == 409
    assert "already been claimed" in exc_info.value.detail
    assert session.rolled_back is True
    assert session.committed is False


@pytest.mark.asyncio
async def test_rider_claim_succeeds_when_update_wins_the_race(monkeypatch):
    order = _order()
    session = _FakeSession(order, update_rowcount=1)
    service = OrderService(session)

    async def fake_load_user(rider_user_id):
        return _rider()

    monkeypatch.setattr(service, "_load_user_with_roles", fake_load_user)
    monkeypatch.setattr(
        "app.modules.orders.service.RiderDispatchService",
        lambda session: _FakeDispatchService(),
    )

    class _RepoStub:
        def __init__(self, order):
            self._order = order

        async def get_by_id(self, order_id):
            return self._order

    service.repo = _RepoStub(order)

    response = await service.rider_claim_order(rider_user_id=17, order_id=1)

    assert session.committed is True
    assert session.rolled_back is False
    assert session.executed_update is not None
    assert response.id == order.id
