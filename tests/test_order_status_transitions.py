from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import OrderService


def _order(*, status, restaurant_id=9, rider_user_id=None):
    return SimpleNamespace(
        id=1,
        restaurant_id=restaurant_id,
        rider_user_id=rider_user_id,
        status=status,
        preparing_at=None,
        delivered_at=None,
        cancelled_at=None,
        rider_offer_expires_at=None,
        restaurant=SimpleNamespace(
            id=restaurant_id, name="Test", slug="test", latitude=None, longitude=None, rider_dispatch_policy="ranked"
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
        cancelled_reason=None,
        rider_assignment_state="unassigned",
        rider_assignment_tier=None,
        rider_offer_id=None,
        rider_offer_tier=None,
        rider_assigned_at=None,
        created_at=datetime.now(UTC),
    )


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        pass


class _RepoStub:
    def __init__(self, order):
        self._order = order

    async def get_by_id(self, order_id):
        return self._order


async def _fake_restaurant_id(merchant_user_id):
    return 9


@pytest.mark.asyncio
async def test_rejects_invalid_status_transition(monkeypatch):
    order = _order(status=OrderStatus.placed)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession()
    service.repo = _RepoStub(order)
    monkeypatch.setattr(service, "_get_active_merchant_restaurant_id", _fake_restaurant_id)

    with pytest.raises(HTTPException) as exc_info:
        # placed -> delivered is not a legal direct jump.
        await service.update_merchant_order_status(1, 1, OrderStatus.delivered)

    assert exc_info.value.status_code == 409
    assert service.session.committed is False


@pytest.mark.asyncio
async def test_valid_transition_records_audit_event(monkeypatch):
    order = _order(status=OrderStatus.placed)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession()
    service.repo = _RepoStub(order)
    monkeypatch.setattr(service, "_get_active_merchant_restaurant_id", _fake_restaurant_id)

    class _FakeDispatchService:
        async def dispatch_next_offer(self, *, order_id):
            pass

    monkeypatch.setattr(
        "app.modules.orders.service.RiderDispatchService", lambda session: _FakeDispatchService()
    )

    response = await service.update_merchant_order_status(1, 1, OrderStatus.preparing)

    assert response.status == OrderStatus.preparing
    assert service.session.committed is True
    assert len(service.session.added) == 1
    event = service.session.added[0]
    assert event.previous_status == "placed"
    assert event.new_status == "preparing"
    assert event.source == "merchant"


@pytest.mark.asyncio
async def test_completing_without_rider_requires_reason_end_to_end(monkeypatch):
    order = _order(status=OrderStatus.preparing, rider_user_id=None)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession()
    service.repo = _RepoStub(order)
    monkeypatch.setattr(service, "_get_active_merchant_restaurant_id", _fake_restaurant_id)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_merchant_order_status(1, 1, OrderStatus.delivered)

    assert exc_info.value.status_code == 400
    assert service.session.committed is False
