from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import OrderService


def _order(*, status, customer_id=5):
    return SimpleNamespace(
        id=1,
        restaurant_id=9,
        rider_user_id=None,
        status=status,
        preparing_at=None,
        delivered_at=None,
        cancelled_at=None,
        rider_offer_expires_at=None,
        restaurant=SimpleNamespace(
            id=9,
            name="Test",
            slug="test",
            latitude=None,
            longitude=None,
            rider_dispatch_policy="ranked",
            logo_url=None,
            primary_cuisine_label=None,
        ),
        customer_id=customer_id,
        customer=SimpleNamespace(full_name="Test Customer"),
        order_number="ORD-TEST01",
        payment_method="cod",
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
        needs_cutlery=True,
        cooking_request=None,
        delivery_instruction=None,
        coupon_discount=0.0,
        delivery_fee=0.0,
        service_fee=0.0,
        tax_amount=0.0,
        subtotal_amount=500.0,
        rider_assignment_state="unassigned",
        rider_assignment_tier=None,
        rider_offer_id=None,
        rider_offer_tier=None,
        rider_assigned_at=None,
        created_at=datetime.now(UTC),
    )


class _FakeSession:
    def __init__(self, rowcount=1):
        self.added = []
        self.committed = False
        self.rolled_back = False
        self._rowcount = rowcount
        self.executed = []

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, stmt):
        self.executed.append(stmt)
        return SimpleNamespace(rowcount=self._rowcount)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        pass


class _RepoStub:
    def __init__(self, order):
        self._order = order

    async def get_order_by_id(self, order_id, customer_id):
        if self._order.customer_id != customer_id:
            return None
        return self._order


@pytest.mark.asyncio
async def test_customer_can_cancel_while_placed():
    order = _order(status=OrderStatus.placed)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession(rowcount=1)
    service.repo = _RepoStub(order)

    response = await service.cancel_order(5, 1, reason="Changed my mind")

    assert service.session.committed is True
    assert len(service.session.added) == 1
    event = service.session.added[0]
    assert event.previous_status == "placed"
    assert event.new_status == "cancelled"
    assert event.source == "customer"
    assert event.note == "Changed my mind"
    # The fake repo returns the same (unmutated) order object on refetch,
    # so we only assert on the audit trail here — the real DB row's status
    # is asserted implicitly by the conditional UPDATE's WHERE clause below.
    assert response.orderNumber == "ORD-TEST01"


@pytest.mark.asyncio
async def test_customer_cannot_cancel_once_preparing():
    order = _order(status=OrderStatus.preparing)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession()
    service.repo = _RepoStub(order)

    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_order(5, 1)

    assert exc_info.value.status_code == 409
    assert service.session.committed is False
    # Rejected before ever attempting the conditional UPDATE.
    assert service.session.executed == []


@pytest.mark.asyncio
async def test_customer_cancel_loses_race_to_merchant():
    """The order looks cancellable when fetched, but the merchant's
    concurrent UPDATE to 'preparing' wins the race — our conditional
    UPDATE affects zero rows, so we must roll back and reject instead of
    reporting success."""
    order = _order(status=OrderStatus.placed)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession(rowcount=0)
    service.repo = _RepoStub(order)

    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_order(5, 1)

    assert exc_info.value.status_code == 409
    assert service.session.rolled_back is True
    assert service.session.committed is False


@pytest.mark.asyncio
async def test_customer_cannot_cancel_someone_elses_order():
    order = _order(status=OrderStatus.placed, customer_id=999)
    service = OrderService.__new__(OrderService)
    service.session = _FakeSession()
    service.repo = _RepoStub(order)

    with pytest.raises(HTTPException) as exc_info:
        await service.cancel_order(5, 1)

    assert exc_info.value.status_code == 404
