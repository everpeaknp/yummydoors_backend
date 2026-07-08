# YummyDoors Backend Agent Guide

## Purpose

This repo is the FastAPI backend for YummyDoors. It is the system of record for:

- auth and role checks
- customer profile and addresses
- restaurants, menus, promos, reservations
- merchant onboarding and workspaces
- carts, orders, reviews, favorites

## Read This First

Before re-auditing the repo, read these local context files first:

- `.codex/context/project-purpose.md`
- `.codex/context/repo-map.md`
- `.codex/context/current-state.md`
- `.codex/context/api-and-auth.md`
- `.codex/context/deployment.md`
- `.codex/context/known-pitfalls.md`

Use the deeper `docs/` files only when the local context files are not enough.

## Repo Boundary

Sibling repos:

- `../yummydoors_desktop` = customer + merchant web surface
- `../yummydoors_admin` = super-admin console
- `../yummydoors_mobile` = Flutter mobile app

Do not change desktop or admin files from this repo by accident. Verify the target repo before editing.

## Verify First

When asked what works "right now", check code and runtime first:

```bash
git status --short
pytest -q
alembic current
rg -n "APIRouter|router =" app
```

For local API runtime:

```bash
docker compose ps
docker compose logs --tail=100 app
```

## Working Rules

- Prefer repo-local context files before broad repo scans.
- Treat Swagger and route code as the source of truth for API availability.
- When the user asks whether something is "done", verify route existence and the user-facing entry point.
- Keep deployment guidance aligned with the current VPS Docker setup unless explicitly changing strategy.
- If an issue might come from desktop or admin consuming the backend incorrectly, check the sibling repo instead of assuming a backend bug.
