# YummyDoors Backend

FastAPI backend foundation for YummyDoors.

## Current scope

- FastAPI app scaffold
- async SQLAlchemy setup
- Alembic migrations
- auth foundation
- local JWT auth with refresh rotation
- RBAC base models
- POS identity linking base models
- homepage discovery foundation

## Quick start

1. Start the local PostgreSQL container:

```bash
docker compose up -d
```

2. Copy `.env.example` to `.env` and update values if needed.
   The backend uses `YUMMYDOORS_`-prefixed variables to avoid collisions with
   machine-level environment variables such as `DEBUG`.
3. Create a virtual environment and install dependencies.
4. Run migrations:

```bash
alembic upgrade heads
```

5. Start the API:

```bash
uvicorn app.main:app --reload
```

Or use the local entrypoint:

```bash
./start.sh
```

If port `8000` is already taken:

```bash
YUMMYDOORS_APP_PORT=8001 ./start.sh
```

## Production deployment

This repo now includes two deployment paths:

- recommended now: VPS production deployment for your current multi-project server
- optional alternative: Cloud Run deployment modeled after `yummy_backend`

Files:

- `Dockerfile`
- `docker-compose.prod.yml`
- `.env.production.example`
- `scripts/entrypoint.sh`
- `scripts/deploy.sh`
- `.github/workflows/deploy-vps.yml`
- `deploy-cloud-run.sh`
- `yummydoors-app.yaml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-cloud-run.yml`
- `docs/DEPLOYMENT_SETUP.md`
- `docs/VPS_PRODUCTION_DEPLOYMENT.md`

The production container runs:

1. `alembic upgrade heads`
2. `gunicorn` with `uvicorn` workers on `${PORT:-8080}`

The repo also includes:

- CI on push and pull request
- Cloud Run deployment from GitHub Actions
- VPS CI/CD deployment from GitHub Actions with env sync

## Local database

YummyDoors uses its own local PostgreSQL container on port `5434` so it does not
conflict with the existing local Postgres container already bound to `5432`.

Default local database values:

- host: `localhost`
- port: `5434`
- database: `yummydoors`
- user: `postgres`
- password: `postgres`

## Auth hardening notes

- Password reset codes are only exposed in API responses when both
  `YUMMYDOORS_DEBUG=true` and `YUMMYDOORS_DEBUG_EXPOSE_RESET_CODE=true`.
- SMTP delivery is ready through the `YUMMYDOORS_SMTP_*` settings.
- Auth-sensitive actions are rate-limited and written to auth audit logs.

## Main endpoints

- `GET /health`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/google`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/auth/me`
- `GET /api/v1/workspaces/me`
- `POST /api/v1/workspaces/switch`
- `GET /api/v1/merchant/applications/me`
- `GET /api/v1/merchant/restaurants/me`
- `POST /api/v1/merchant/applications`
- `POST /api/v1/merchant/restaurants/switch`
- `GET /api/v1/merchant/applications/{application_id}`
- `PATCH /api/v1/merchant/applications/{application_id}`
- `POST /api/v1/merchant/applications/{application_id}/restaurant-requests`
- `POST /api/v1/merchant/applications/{application_id}/submit`
- `GET /api/v1/admin/merchant-applications`
- `POST /api/v1/admin/merchant-applications/{application_id}/approve`
- `POST /api/v1/admin/merchant-applications/{application_id}/reject`
- `GET /api/v1/restaurants`
- `GET /api/v1/restaurants/{slug}`
- `GET /api/v1/home/feed`

## Superuser bootstrap

Create or update the initial Doors superuser:

```bash
yummydoors-create-superuser \
  --email admin@yummydoors.local \
  --password 'ChangeMe123!' \
  --full-name 'YummyDoors Super Admin'
```

## Homepage bootstrap

Seed the first homepage/discovery data after a fresh local reset:

```bash
yummydoors-seed-homepage --reset
```

This seeds:

- featured homepage categories
- starter active restaurants
- restaurant to category mappings

The first customer-facing backend contract is now:

- `GET /api/v1/home/feed`
  - location context
  - featured categories
  - restaurant cards
- `GET /api/v1/restaurants`
  - active restaurant discovery feed
