from __future__ import annotations

import logging
from datetime import UTC, datetime

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.orders.models import Order
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.schemas import EsewaVerifyRequest

logger = logging.getLogger(__name__)

_ESEWA_LIVE_BASE_URL = "https://esewa.com.np"
_ESEWA_TEST_BASE_URL = "https://rc.esewa.com.np"


class PaymentService:
    """Server-side payment verification and the payment ledger.

    This intentionally verifies with the payment provider itself rather than
    trusting a client-asserted "payment succeeded" flag — the eSewa merchant
    secret used for that call lives only in backend settings and is never
    sent to any client.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def verify_esewa_payment(
        self, *, customer_id: int, payload: EsewaVerifyRequest
    ) -> Payment:
        order = await self.session.get(Order, payload.order_id)
        if order is None or order.customer_id != customer_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found.")

        if order.payment_status == "paid":
            existing = await self._get_latest_payment(order.id)
            if existing is not None:
                return existing

        if not settings.esewa_client_id or not settings.esewa_secret_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="eSewa is not configured on the server.",
            )

        now = datetime.now(UTC)
        payment = Payment(
            order_id=order.id,
            method="esewa",
            provider="esewa",
            provider_ref=payload.ref_id,
            amount=order.total_price,
            status=PaymentStatus.pending,
            initiated_at=now,
        )
        self.session.add(payment)
        await self.session.flush()

        try:
            raw_response = await self._call_esewa_verify(payload)
        except httpx.HTTPError as exc:
            logger.warning("eSewa verification request failed order_id=%s: %s", order.id, exc)
            payment.status = PaymentStatus.failed
            payment.failure_reason = "Unable to reach eSewa for verification."
            payment.failed_at = datetime.now(UTC)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to verify payment with eSewa right now.",
            ) from exc

        payment.raw_response = raw_response

        verified, reference_id, failure_reason = self._parse_esewa_response(raw_response)
        if verified:
            payment.status = PaymentStatus.verified
            payment.confirmed_at = datetime.now(UTC)
            if reference_id:
                payment.provider_ref = reference_id
            order.payment_status = "paid"
        else:
            payment.status = PaymentStatus.failed
            payment.failure_reason = failure_reason or "eSewa transaction is not complete."
            payment.failed_at = datetime.now(UTC)

        await self.session.commit()
        await self.session.refresh(payment)

        if not verified:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=payment.failure_reason,
            )

        return payment

    async def _get_latest_payment(self, order_id: int) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.order_id == order_id).order_by(Payment.id.desc())
        )
        return result.scalars().first()

    async def _call_esewa_verify(self, payload: EsewaVerifyRequest) -> dict:
        base_url = (
            _ESEWA_LIVE_BASE_URL
            if settings.esewa_environment.lower() == "live"
            else _ESEWA_TEST_BASE_URL
        )
        params: dict[str, str | float] = {}
        if payload.ref_id:
            params["txnRefId"] = payload.ref_id
        elif payload.product_id and payload.amount is not None:
            params["productId"] = payload.product_id
            params["amount"] = payload.amount
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ref_id, or product_id and amount, are required.",
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{base_url}/mobile/transaction",
                params=params,
                headers={
                    "merchantId": settings.esewa_client_id or "",
                    "merchantSecret": settings.esewa_secret_key or "",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}

    @staticmethod
    def _parse_esewa_response(raw_response: dict) -> tuple[bool, str | None, str | None]:
        items = raw_response.get("data") if isinstance(raw_response.get("data"), list) else None
        if items is None and isinstance(raw_response, dict):
            items = [raw_response]
        if not items:
            return False, None, "eSewa returned an empty verification response."

        first = items[0] if isinstance(items[0], dict) else {}
        transaction_details = first.get("transactionDetails") or {}
        message = first.get("message") or {}
        tx_status = str(transaction_details.get("status") or "").strip().upper()
        reference_id = str(transaction_details.get("referenceId") or "").strip() or None

        if tx_status != "COMPLETE":
            failure_message = (
                message.get("technicalSuccessMessage")
                or message.get("successMessage")
                or "eSewa transaction is not complete."
            )
            return False, reference_id, str(failure_message)

        return True, reference_id, None
