from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import require_role
from app.modules.promotions.models import Promotion
from app.modules.promotions.repository import PromotionRepository
from app.modules.promotions.schemas import (
    PromotionCreateRequest,
    PromotionResponse,
    PromotionUpdateRequest,
)

router = APIRouter(prefix="/admin/promotions", tags=["Admin Promotions"])


def _format(promotion: Promotion) -> PromotionResponse:
    return PromotionResponse(
        id=promotion.id,
        code=promotion.code,
        discountType=promotion.discount_type,
        discountValue=promotion.discount_value,
        maxDiscountAmount=promotion.max_discount_amount,
        minOrderAmount=promotion.min_order_amount,
        restaurantId=promotion.restaurant_id,
        restaurantName=promotion.restaurant.name if promotion.restaurant else None,
        isActive=promotion.is_active,
        startsAt=promotion.starts_at,
        expiresAt=promotion.expires_at,
        usageLimit=promotion.usage_limit,
        perUserLimit=promotion.per_user_limit,
        timesUsed=promotion.times_used,
        description=promotion.description,
        createdAt=promotion.created_at,
    )


@router.get(
    "",
    response_model=List[PromotionResponse],
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def list_promotions(
    restaurant_id: int | None = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    repo = PromotionRepository(db)
    promotions = await repo.list_all(restaurant_id=restaurant_id, active_only=active_only)
    return [_format(p) for p in promotions]


@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def create_promotion(
    payload: PromotionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = PromotionRepository(db)
    existing = await repo.get_by_code(payload.code)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A coupon with this code already exists.")

    promotion = await repo.create(
        code=payload.code,
        discount_type=payload.discountType,
        discount_value=payload.discountValue,
        max_discount_amount=payload.maxDiscountAmount,
        min_order_amount=payload.minOrderAmount,
        restaurant_id=payload.restaurantId,
        starts_at=payload.startsAt,
        expires_at=payload.expiresAt,
        usage_limit=payload.usageLimit,
        per_user_limit=payload.perUserLimit,
        description=payload.description,
    )
    return _format(promotion)


@router.patch(
    "/{promotion_id}",
    response_model=PromotionResponse,
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def update_promotion(
    promotion_id: int,
    payload: PromotionUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    repo = PromotionRepository(db)
    promotion = await repo.get_by_id(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")

    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "discountType": "discount_type",
        "discountValue": "discount_value",
        "maxDiscountAmount": "max_discount_amount",
        "minOrderAmount": "min_order_amount",
        "restaurantId": "restaurant_id",
        "isActive": "is_active",
        "startsAt": "starts_at",
        "expiresAt": "expires_at",
        "usageLimit": "usage_limit",
        "perUserLimit": "per_user_limit",
        "description": "description",
    }
    model_fields = {field_map[key]: value for key, value in updates.items() if key in field_map}
    promotion = await repo.update(promotion, model_fields)
    return _format(promotion)


@router.delete(
    "/{promotion_id}",
    dependencies=[Depends(require_role(["super_admin", "ops_admin"]))],
)
async def delete_promotion(
    promotion_id: int,
    db: AsyncSession = Depends(get_db),
):
    repo = PromotionRepository(db)
    promotion = await repo.get_by_id(promotion_id)
    if promotion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")
    await repo.delete(promotion)
    return {"message": "Coupon deleted."}
