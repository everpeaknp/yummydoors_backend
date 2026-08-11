from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.modules.auth.deps import get_current_user
from app.modules.auth.models import User
from app.modules.promotions.repository import PromotionRepository
from app.modules.promotions.schemas import PromotionResponse, format_promotion_response
from app.modules.promotions.merchant_schemas import (
    MerchantPromotionCreateRequest,
    MerchantPromotionUpdateRequest,
)
from app.modules.workspaces.repository import WorkspaceRepository

router = APIRouter(prefix="/merchant/promotions", tags=["Merchant Promotions"])


async def _get_merchant_restaurant_id(user_id: int, session: AsyncSession) -> int:
    workspace_repo = WorkspaceRepository(session)
    restaurant_id = await workspace_repo.get_active_merchant_restaurant_id(user_id)
    if not restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active workspace is not a merchant workspace.",
        )
    return restaurant_id


@router.get("", response_model=List[PromotionResponse])
async def list_my_promotions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = PromotionRepository(db)
    promotions = await repo.list_all(restaurant_id=restaurant_id)
    return [format_promotion_response(p) for p in promotions]


@router.post("", response_model=PromotionResponse, status_code=status.HTTP_201_CREATED)
async def create_my_promotion(
    payload: MerchantPromotionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
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
        restaurant_id=restaurant_id,
        starts_at=payload.startsAt,
        expires_at=payload.expiresAt,
        usage_limit=payload.usageLimit,
        per_user_limit=payload.perUserLimit,
        description=payload.description,
    )
    return format_promotion_response(promotion)


@router.patch("/{promotion_id}", response_model=PromotionResponse)
async def update_my_promotion(
    promotion_id: int,
    payload: MerchantPromotionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = PromotionRepository(db)
    promotion = await repo.get_by_id(promotion_id)
    if promotion is None or promotion.restaurant_id != restaurant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")

    updates = payload.model_dump(exclude_unset=True)
    field_map = {
        "discountType": "discount_type",
        "discountValue": "discount_value",
        "maxDiscountAmount": "max_discount_amount",
        "minOrderAmount": "min_order_amount",
        "isActive": "is_active",
        "startsAt": "starts_at",
        "expiresAt": "expires_at",
        "usageLimit": "usage_limit",
        "perUserLimit": "per_user_limit",
        "description": "description",
    }
    model_fields = {field_map[key]: value for key, value in updates.items() if key in field_map}
    promotion = await repo.update(promotion, model_fields)
    return format_promotion_response(promotion)


@router.delete("/{promotion_id}")
async def delete_my_promotion(
    promotion_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    restaurant_id = await _get_merchant_restaurant_id(current_user.id, db)
    repo = PromotionRepository(db)
    promotion = await repo.get_by_id(promotion_id)
    if promotion is None or promotion.restaurant_id != restaurant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found.")
    await repo.delete(promotion)
    return {"message": "Coupon deleted."}
