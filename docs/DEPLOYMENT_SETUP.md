# YummyDoors Backend Deployment Setup

## Current recommendation

For your current infrastructure, use the VPS production path in
`docs/VPS_PRODUCTION_DEPLOYMENT.md`.

Cloud Run remains a valid managed-cloud alternative, but it is no longer the
primary recommendation for the multi-project server you showed.

## What we are copying from `yummy_backend`

`yummy_backend` is already using the right deployment shape for a FastAPI service:

- container-first deployment
- `uvicorn` bound to `${PORT:-8080}`
- migrations run during container startup
- Cloud Run deployment script
- optional Azure Container Apps manifest

That is a better fit for `yummydoors_backend` than a VPS-style long-running
manual process.

## What was added here

- `Dockerfile`
- `.dockerignore`
- `deploy-cloud-run.sh`
- `yummydoors-app.yaml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-cloud-run.yml`
- `docker-compose.prod.yml`
- `.env.production.example`
- `scripts/entrypoint.sh`
- `scripts/deploy.sh`
- `.github/workflows/deploy-vps.yml`

## Deployment philosophy

Use one image for all environments.

Container startup should:

1. start with production env vars
2. run `alembic upgrade heads`
3. start `uvicorn` on port `8080`

This keeps schema migration explicit and consistent across local, Cloud Run, and
Container Apps.

## Cloud Run

### First deploy

```bash
PROJECT_ID=your-gcp-project ./deploy-cloud-run.sh
```

### GitHub Actions deploy

This repo now has a Cloud Run deploy workflow.

Required GitHub repository secrets:

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `CLOUD_RUN_SERVICE`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`

Recommended values:

- `GCP_REGION=asia-south1`
- `CLOUD_RUN_SERVICE=yummydoors-backend`
- `ARTIFACT_REGISTRY_REPOSITORY=yummydoors-backend`

### Required env vars in Cloud Run

Set these in the platform, not in the repo:

- `YUMMYDOORS_DATABASE_URL`
- `YUMMYDOORS_POS_DATABASE_URL`
- `YUMMYDOORS_JWT_SECRET_KEY`
- `YUMMYDOORS_SMTP_USERNAME`
- `YUMMYDOORS_SMTP_PASSWORD`
- `YUMMYDOORS_GOOGLE_CLIENT_ID`

Recommended production values:

- `YUMMYDOORS_APP_ENV=production`
- `YUMMYDOORS_DEBUG=false`
- `YUMMYDOORS_DB_ECHO=false`
- `YUMMYDOORS_DEBUG_EXPOSE_RESET_CODE=false`

## Azure Container Apps

`yummydoors-app.yaml` is a clean template only.

Before using it, replace:

- `CHANGE_ME` resource group
- `CHANGE_ME.azurecr.io` registry
- secret references with real platform secrets
- production CORS origins

Do not hardcode secrets into the YAML.

## Validation before deploy

### Build image locally

```bash
docker build -t yummydoors-backend:local .
```

### Run image locally

```bash
docker run --rm -p 8080:8080 --env-file .env yummydoors-backend:local
```

### Health check

```bash
curl http://127.0.0.1:8080/health
```

## Notes

- Local `start.sh` remains the developer entrypoint.
- The production container does not use `--reload`.
- SQL logging is already separated from app debug via `YUMMYDOORS_DB_ECHO`.
- CI runs lint, app compile, and tests when a `tests/` directory exists.
