from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base  # noqa: F401
from app.modules.admin.api import router as admin_router
from app.modules.auth.api import router as auth_router
from app.modules.catalog.api import router as catalog_router
from app.modules.customers.api import router as customer_router
from app.modules.favorites.api import router as favorites_router
from app.modules.merchandising.api import router as merchandising_router
from app.modules.reservations.api import router as reservations_router
from app.modules.restaurants.api import router as restaurant_router
from app.modules.workspaces.api import router as workspace_router

from app.modules.carts.api import router as carts_router
from app.modules.orders.api import router as orders_router
from app.modules.messages.api import router as messages_router
from app.modules.reviews.api import router as reviews_router
from app.modules.media.api import router as media_router
from app.modules.notifications.api import router as notifications_router

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Authentication, token lifecycle, password reset, and current-user auth session endpoints.",
    },
    {
        "name": "Admin",
        "description": "Admin-only ingestion and approval surfaces for restaurants, menu structure, promos, and merchant onboarding.",
    },
    {
        "name": "restaurants",
        "description": "Customer-facing restaurant discovery, restaurant detail, home feed, and public reviews endpoints.",
    },
    {
        "name": "Customers",
        "description": "Authenticated customer profile and saved-address management endpoints.",
    },
    {
        "name": "Favorites",
        "description": "Customer wishlist and saved favorite restaurants or menu items.",
    },
    {
        "name": "Catalog",
        "description": "Restaurant category and menu item management endpoints used by merchant or admin flows.",
    },
    {
        "name": "Merchandising",
        "description": "Homepage, banner, and promo merchandising management endpoints.",
    },
    {
        "name": "Workspaces",
        "description": "Merchant/customer multi-workspace, onboarding, and restaurant claim/create request flows.",
    },
    {
        "name": "Carts",
        "description": "Cart item, cart context, and starter coupon application endpoints for customer checkout flows.",
    },
    {
        "name": "Orders",
        "description": "Checkout, placed-order history, and order detail endpoints.",
    },
    {
        "name": "Messages",
        "description": "Merchant-customer direct messaging with WebSocket real-time support.",
    },
    {
        "name": "Reviews",
        "description": "Customer reviews for restaurants, and merchant reply endpoints.",
    },
    {
        "name": "Reservations",
        "description": "Table-booking availability, table inventory, customer reservations, and merchant reservation-management endpoints.",
    },
    {
        "name": "Notifications",
        "description": "Browser push subscription management and web push configuration endpoints.",
    },
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "YummyDoors API for customer, merchant, restaurant, merchandising, "
        "workspace, cart, and order flows."
    ),
    version="0.1.0",
    debug=settings.debug,
    lifespan=lifespan,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:3000", "http://127.0.0.1:3000", "https://yummydoors.everacy.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(restaurant_router, prefix=settings.api_v1_prefix)
app.include_router(customer_router, prefix=settings.api_v1_prefix)
app.include_router(favorites_router, prefix=settings.api_v1_prefix)
app.include_router(catalog_router, prefix=settings.api_v1_prefix)
app.include_router(merchandising_router, prefix=settings.api_v1_prefix)
app.include_router(workspace_router, prefix=settings.api_v1_prefix)
app.include_router(carts_router, prefix=settings.api_v1_prefix)
app.include_router(orders_router, prefix=settings.api_v1_prefix)
app.include_router(reservations_router, prefix=settings.api_v1_prefix)
app.include_router(messages_router, prefix=settings.api_v1_prefix)
app.include_router(reviews_router, prefix=settings.api_v1_prefix)
app.include_router(media_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}

@app.get("/version")
async def get_version() -> dict:
    return {"version": "v-diag-1"}
