import pytest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

# Instantiating Payment() below configures the full SQLAlchemy mapper
# registry (Payment -> Order -> User/Restaurant/...), so the whole app must
# be imported first to register every model, not just the ones this file
# references directly.
import app.main  # noqa: F401
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.schemas import EsewaVerifyRequest
from app.modules.payments.service import PaymentService


class _FakeOrder:
    def __init__(self, id=1, customer_id=7, total_price=500.0, payment_status="unpaid"):
        self.id = id
        self.customer_id = customer_id
        self.total_price = total_price
        self.payment_status = payment_status


class _FakeScalars:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _FakeScalars(self._items)


class _FakeSession:
    def __init__(self, order):
        self._order = order
        self.added = []
        self.committed = False

    async def get(self, model, id):
        assert model is Order
        return self._order if self._order and self._order.id == id else None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        return _FakeResult([])


def _complete_esewa_response(reference_id="0000ABC"):
    return {
        "data": [
            {
                "transactionDetails": {"status": "COMPLETE", "referenceId": reference_id},
                "message": {},
            }
        ]
    }


def _incomplete_esewa_response():
    return {
        "data": [
            {
                "transactionDetails": {"status": "PENDING", "referenceId": ""},
                "message": {"successMessage": "Transaction is pending."},
            }
        ]
    }


@pytest.mark.asyncio
async def test_verify_esewa_payment_success(monkeypatch):
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_client_id", "client-123")
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_secret_key", "secret-456")
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_environment", "test")

    order = _FakeOrder()
    session = _FakeSession(order)
    service = PaymentService(session)

    with patch.object(
        PaymentService, "_call_esewa_verify", new=AsyncMock(return_value=_complete_esewa_response())
    ):
        payment = await service.verify_esewa_payment(
            customer_id=7,
            payload=EsewaVerifyRequest(order_id=1, ref_id="txn-ref-1"),
        )

    assert payment.status == PaymentStatus.verified
    assert payment.provider_ref == "0000ABC"
    assert order.payment_status == "paid"
    assert session.committed is True


@pytest.mark.asyncio
async def test_verify_esewa_payment_incomplete_transaction_rejected(monkeypatch):
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_client_id", "client-123")
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_secret_key", "secret-456")

    order = _FakeOrder()
    session = _FakeSession(order)
    service = PaymentService(session)

    with patch.object(
        PaymentService, "_call_esewa_verify", new=AsyncMock(return_value=_incomplete_esewa_response())
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.verify_esewa_payment(
                customer_id=7,
                payload=EsewaVerifyRequest(order_id=1, ref_id="txn-ref-1"),
            )

    assert exc_info.value.status_code == 402
    assert order.payment_status == "unpaid"


@pytest.mark.asyncio
async def test_verify_esewa_payment_requires_server_config(monkeypatch):
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_client_id", None)
    monkeypatch.setattr("app.modules.payments.service.settings.esewa_secret_key", None)

    order = _FakeOrder()
    session = _FakeSession(order)
    service = PaymentService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_esewa_payment(
            customer_id=7,
            payload=EsewaVerifyRequest(order_id=1, ref_id="txn-ref-1"),
        )

    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_esewa_payment_rejects_order_not_owned_by_caller():
    order = _FakeOrder(customer_id=99)
    session = _FakeSession(order)
    service = PaymentService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_esewa_payment(
            customer_id=7,
            payload=EsewaVerifyRequest(order_id=1, ref_id="txn-ref-1"),
        )

    assert exc_info.value.status_code == 404
