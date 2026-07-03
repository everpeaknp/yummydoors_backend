from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
import enum
from sqlalchemy import Enum as SQLEnum

from app.db.session import Base
from app.models.mixins import TimestampMixin

class PromoPlacement(str, enum.Enum):
    home_carousel = "home_carousel"
    home_banner = "home_banner"

class PromoTargetType(str, enum.Enum):
    restaurant = "restaurant"
    category = "category"
    menu_item = "menu_item"
    url = "url"
    none = "none"

class PromoBanner(Base, TimestampMixin):
    __tablename__ = "promo_banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    placement: Mapped[PromoPlacement] = mapped_column(SQLEnum(PromoPlacement), default=PromoPlacement.home_carousel, nullable=False)
    target_type: Mapped[PromoTargetType] = mapped_column(SQLEnum(PromoTargetType), default=PromoTargetType.none, nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    cta_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
