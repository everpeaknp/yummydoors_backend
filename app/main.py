from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base  # noqa: F401
from app.modules.admin.api import router as admin_router
from app.modules.auth.api import router as auth_router
from app.modules.catalog.api import router as catalog_router
from app.modules.customers.api import router as customer_router
from app.modules.merchandising.api import router as merchandising_router
from app.modules.restaurants.api import router as restaurant_router
from app.modules.workspaces.api import router as workspace_router

from app.modules.carts.api import router as carts_router
from app.modules.orders.api import router as orders_router


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
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(restaurant_router, prefix=settings.api_v1_prefix)
app.include_router(customer_router, prefix=settings.api_v1_prefix)
app.include_router(catalog_router, prefix=settings.api_v1_prefix)
app.include_router(merchandising_router, prefix=settings.api_v1_prefix)
app.include_router(workspace_router, prefix=settings.api_v1_prefix)
app.include_router(carts_router, prefix=settings.api_v1_prefix)
app.include_router(orders_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
