# YummyDoors VPS Production Deployment

## Recommended deployment for your current server

For the current server layout we verified, the active production model is:

- Docker Compose on the VPS
- image-based deploys using `ramoniswack/yummydoors-backend:latest`
- app exposed only on `127.0.0.1`
- host-level reverse proxy in front of it
- GitHub Actions CI/CD with SSH deploy

This is a better fit for your current box than forcing Cloud Run patterns onto a
multi-project VPS.

## Files added for production

- `docker-compose.prod.yml`
- `.env.production.example`
- `scripts/entrypoint.sh`
- `scripts/deploy.sh`
- `.github/workflows/ci.yml`

## First-time server setup

### 1. Prepare the VPS project folder

```bash
cd ~/yummydoors_backend
```

### 2. Prepare env file

```bash
touch .env.production
```

Set at minimum:

- `YUMMYDOORS_POSTGRES_PASSWORD`
- `YUMMYDOORS_DATABASE_URL`
- `YUMMYDOORS_JWT_SECRET_KEY`
- `YUMMYDOORS_CORS_ORIGINS`
- SMTP credentials

### 3. Deploy manually if needed

```bash
docker compose pull
docker compose up -d --force-recreate app
```

## GitHub Actions CI/CD

This repo is now set so that:

- pull requests and pushes run CI
- pushes to `main` build and push the Docker image, then run VPS deploy
- the server pulls the latest image and recreates the `app` service

### Required GitHub Secrets

- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `VPS_HOST`
- `VPS_PORT`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PROJECT_PATH`

### 4. Check runtime

```bash
docker compose ps
docker compose logs -f app
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
- Alembic migrations run during app startup
- app port bound to localhost only
- GitHub Actions CI gate before deploy
- production image pull and app recreate on every deploy

## Notes

- Current app features do not require Redis, so it is intentionally not added.
- If you later add background jobs, then add a worker profile instead of
  bloating the default stack now.
- If you change production env values, update the `ENV_PRODUCTION` GitHub secret
  and trigger the deploy workflow again.
