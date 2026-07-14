# YummyDoors Backend Agent Guide

## Purpose

This repo is the FastAPI backend for YummyDoors. It is the system of record for:

- auth and role checks
- customer profile and addresses
- restaurants, menus, promos, reservations
- merchant onboarding and workspaces
- carts, orders, reviews, favorites

## Context Files — Read Only What's Relevant

Don't read all of these on every task. Pick based on what the task touches:

- Task involves auth, tokens, permissions, endpoint contracts → `.codex/context/api-and-auth.md`
- Task asks "is X done / what exists" → `.codex/context/current-state.md`
- Task involves docker, VPS, env vars, CI → `.codex/context/deployment.md`
- New session / unfamiliar area of repo → `.codex/context/repo-map.md`
- Task requires understanding *why*, not just *what* → `.codex/context/project-purpose.md`

Always skim `.codex/context/known-pitfalls.md` first for any non-trivial change — it's cheap and prevents repeated mistakes.

Use the deeper `docs/` files only when the local context files are not enough.

## Repo Boundary

Sibling repos (relative, same parent folder):

- `../yummydoors_desktop` = customer + merchant web surface
- `../yummydoors_admin` = super-admin console

Other repos (not a relative sibling — different mount):

- `/mnt/d/Windows_Projects/yummy-user` = Flutter mobile app (Windows-side repo, accessed via WSL mount)

Do not change desktop or admin files from this repo by accident. Verify the target repo before editing. If an issue might be caused by the mobile app, check `/mnt/d/Windows_Projects/yummy-user` directly using its absolute path — don't assume it's reachable via `../`.

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

Don't re-run these commands more than once per session unless files have changed since the last run.

## Working Rules

- Prefer repo-local context files before broad repo scans.
- Treat Swagger and route code as the source of truth for API availability.
- When the user asks whether something is "done", verify route existence and the user-facing entry point.
- Keep deployment guidance aligned with the current VPS Docker setup unless explicitly changing strategy.
- If an issue might come from desktop or admin consuming the backend incorrectly, check the sibling repo instead of assuming a backend bug.
- If an issue might come from the mobile app consuming the backend incorrectly, check `/mnt/d/Windows_Projects/yummy-user` instead of assuming a backend bug.