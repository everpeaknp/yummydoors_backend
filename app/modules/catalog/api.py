from typing import List
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.modules.catalog.schemas import MenuItemResponse
from app.modules.catalog.service import CatalogService

router = APIRouter(tags=["catalog"])


@router.get("/restaurants/{restaurant_id}/menu", response_model=ApiResponse[List[MenuItemResponse]])
async def get_restaurant_menu(
    restaurant_id: int,
    db: AsyncSession = Depends(get_db)
):
    service = CatalogService(db)
    items = await service.get_restaurant_menu(restaurant_id)
    return ApiResponse(message="Menu fetched successfully.", data=items)


@router.get("/menu-items/{slug}", response_model=ApiResponse[MenuItemResponse])
async def get_menu_item(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    service = CatalogService(db)
    item = await service.get_menu_item_by_slug(slug)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        
    return ApiResponse(message="Menu item fetched successfully.", data=item)
