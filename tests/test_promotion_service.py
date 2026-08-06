from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

import app.main  # noqa: F401 — registers the full SQLAlchemy mapper graph.
from app.modules.promotions.models import Promotion, PromotionDiscountType
from app.modules.promotions.service import PromotionService


def _promotion(**overrides) -> Promotion:
    defaults = dict(
        id=1,
        code="SAVE10",
        discount_type=PromotionDiscountType.percentage,
        discount_value=10.0,
        max_discount_amount=None,
        min_order_amount=0.0,
        restaurant_id=None,
        is_active=True,
        starts_at=None,
        expires_at=None,
        usage_limit=None,
        per_user_limit=None,
        times_used=0,
    )
    defaults.update(overrides)
    return Promotion(**defaults)


class _FakeRepo:
    def __init__(self, promotion: Promotion | None, *, redemptions_for_user: int = 0, claim_succeeds: bool = True):
        self.promotion = promotion
        self.redemptions_for_user = redemptions_for_user
        self.claim_succeeds = claim_succeeds
        self.recorded = None

    async def get_by_code(self, code):
        return self.promotion

    async def count_redemptions_for_user(self, *, promotion_id, customer_id):
        return self.redemptions_for_user

    async def try_claim_usage_slot(self, promotion_id):
        return self.claim_succeeds

    async def record_redemption(self, **kwargs):
        self.recorded = kwargs
        return None


def _service(repo: _FakeRepo) -> PromotionService:
    service = PromotionService.__new__(PromotionService)
    service.session = None
    service.repo = repo
    return service


@pytest.mark.asyncio
async def test_percentage_coupon_computes_discount():
    service = _service(_FakeRepo(_promotion(discount_type=PromotionDiscountType.percentage, discount_value=10.0)))

    quote = await service.quote_discount(code="save10", restaurant_id=1, customer_id=5, items_total=200.0)

    assert quote.discount_amount == 20.0
    assert quote.free_delivery is False


@pytest.mark.asyncio
async def test_percentage_coupon_respects_max_discount_cap():
    service = _service(
        _FakeRepo(
            _promotion(
                discount_type=PromotionDiscountType.percentage,
                discount_value=50.0,
                max_discount_amount=30.0,
            )
        )
    )

    quote = await service.quote_discount(code="save10", restaurant_id=1, customer_id=5, items_total=200.0)

    assert quote.discount_amount == 30.0


@pytest.mark.asyncio
async def test_free_delivery_coupon_has_zero_discount_but_flag_set():
    service = _service(_FakeRepo(_promotion(discount_type=PromotionDiscountType.free_delivery, discount_value=0.0)))

    quote = await service.quote_discount(code="freedel", restaurant_id=1, customer_id=5, items_total=200.0)

    assert quote.discount_amount == 0.0
    assert quote.free_delivery is True


@pytest.mark.asyncio
async def test_unknown_code_raises_400():
    service = _service(_FakeRepo(None))

    with pytest.raises(HTTPException) as exc_info:
        await service.quote_discount(code="NOPE", restaurant_id=1, customer_id=5, items_total=100.0)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_inactive_coupon_is_rejected():
    service = _service(_FakeRepo(_promotion(is_active=False)))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_expired_coupon_is_rejected():
    service = _service(_FakeRepo(_promotion(expires_at=datetime.now(UTC) - timedelta(days=1))))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_coupon_scoped_to_a_different_restaurant_is_rejected():
    service = _service(_FakeRepo(_promotion(restaurant_id=9)))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_below_minimum_order_amount_is_rejected():
    service = _service(_FakeRepo(_promotion(min_order_amount=500.0)))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_usage_limit_fully_redeemed_is_rejected():
    service = _service(_FakeRepo(_promotion(usage_limit=10, times_used=10)))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_per_user_limit_reached_is_rejected():
    service = _service(_FakeRepo(_promotion(per_user_limit=1), redemptions_for_user=1))

    with pytest.raises(HTTPException):
        await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=5, items_total=100.0)


@pytest.mark.asyncio
async def test_anonymous_preview_skips_per_user_limit_check():
    service = _service(_FakeRepo(_promotion(per_user_limit=1), redemptions_for_user=99))

    quote = await service.quote_discount(code="SAVE10", restaurant_id=1, customer_id=None, items_total=100.0)

    assert quote.discount_amount == 10.0


@pytest.mark.asyncio
async def test_redeem_records_redemption_when_claim_succeeds():
    repo = _FakeRepo(_promotion(), claim_succeeds=True)
    service = _service(repo)

    await service.redeem(code="SAVE10", customer_id=5, order_id=42, discount_amount=20.0)

    assert repo.recorded == {
        "promotion_id": 1,
        "customer_id": 5,
        "order_id": 42,
        "discount_amount": 20.0,
    }


@pytest.mark.asyncio
async def test_redeem_raises_409_when_usage_slot_race_is_lost():
    repo = _FakeRepo(_promotion(), claim_succeeds=False)
    service = _service(repo)

    with pytest.raises(HTTPException) as exc_info:
        await service.redeem(code="SAVE10", customer_id=5, order_id=42, discount_amount=20.0)

    assert exc_info.value.status_code == 409
    assert repo.recorded is None
