# YummyDoors VPS Production Deployment

## Recommended deployment for your current server

For the server layout you showed, the strongest deployment model is:

- one repo checkout on the VPS
- Docker Compose for app plus PostgreSQL
- app exposed only on `127.0.0.1`
- host-level reverse proxy in front of it
- deploys through `scripts/deploy.sh`
- GitHub Actions CI/CD with SSH deploy

This is a better fit for your current box than forcing Cloud Run patterns onto a
multi-project VPS.

## Files added for production

- `docker-compose.prod.yml`
- `.env.production.example`
- `scripts/entrypoint.sh`
- `scripts/deploy.sh`
- `.github/workflows/deploy-vps.yml`
- `.github/workflows/ci.yml`

## First-time server setup

### 1. Clone repo on the server

```bash
cd ~
git clone git@github.com:everpeaknp/yummydoors_backend.git
cd yummydoors_backend
```

### 2. Prepare env file

```bash
cp .env.production.example .env.production
```

Set at minimum:

- `YUMMYDOORS_POSTGRES_PASSWORD`
- `YUMMYDOORS_DATABASE_URL`
- `YUMMYDOORS_JWT_SECRET_KEY`
- `YUMMYDOORS_CORS_ORIGINS`
- SMTP credentials

### 3. Deploy

```bash
bash scripts/deploy.sh
```

## GitHub Actions CI/CD

This repo is now set so that:

- pull requests and pushes run CI
- pushes to `main` run deploy after quality checks pass
- the production env file is re-synced to the server on every deploy

### Required GitHub Secrets

- `VPS_HOST`
- `VPS_PORT`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PROJECT_PATH`
- `ENV_PRODUCTION`

### Important env rule

`ENV_PRODUCTION` should contain the full contents of `.env.production`.

That means:

- code changes deploy from git
- env changes deploy from GitHub secret updates
- the server does not silently drift from the CI/CD source of truth

### 4. Check runtime

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f app
curl http://127.0.0.1:8010/health
```

## Reverse proxy recommendation

Do not expose the app container directly to the public internet.

Use your shared host reverse proxy to map a domain such as:

- `doors-api.yourdomain.com` -> `127.0.0.1:8010`

That keeps TLS and public routing centralized across your server.

## Why this setup is production-grade

- non-root app container
- Gunicorn with Uvicorn workers
- PostgreSQL healthchecks
- startup waits for DB readiness
- Alembic migrations run during deploy startup
- app port bound to localhost only
- repeatable deploy script
- GitHub Actions CI gate before deploy
- production env sync on every deploy

## Notes

- Current app features do not require Redis, so it is intentionally not added.
- If you later add background jobs, then add a worker profile instead of
  bloating the default stack now.
- If you change production env values, update the `ENV_PRODUCTION` GitHub secret
  and trigger the deploy workflow again.
