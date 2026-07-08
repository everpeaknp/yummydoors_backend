# Repo Map

## Main App

- `app/main.py` = FastAPI app, middleware, router registration, OpenAPI tags
- `app/core/config.py` = settings and env parsing
- `app/db/` = SQLAlchemy base and session
- `app/modules/` = domain modules

## Key Modules

- `app/modules/auth/` = login, refresh, admin login, password flows, auth deps
- `app/modules/customers/` = customer profile and saved addresses
- `app/modules/restaurants/` = customer discovery and restaurant detail
- `app/modules/catalog/` = restaurant categories and menu items
- `app/modules/favorites/` = wishlist / favorites
- `app/modules/reviews/` = restaurant review write/read flows
- `app/modules/carts/` = cart and coupon application starter flows
- `app/modules/orders/` = checkout and order history/detail
- `app/modules/reservations/` = booking availability and reservation management
- `app/modules/workspaces/` = merchant/customer workspace switching and onboarding
- `app/modules/admin/` = super-admin actions
- `app/modules/merchandising/` = promos and homepage merchandising

## Operational Files

- `migrations/` = Alembic migrations
- `docker-compose.yml` = local stack
- `docker-compose.prod.yml` = production-oriented stack
- `start.sh` = local startup helper
- `docs/` = deeper architecture and rollout docs
- `tests/` = targeted backend tests
