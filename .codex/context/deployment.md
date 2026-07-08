# Deployment Notes

## Current Production Style

Current live deployment is VPS Docker based.

Important files:

- `docker-compose.prod.yml`
- `vps-docker-compose.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/deploy-vps.yml`

## Local Checks

```bash
docker compose ps
docker compose logs --tail=100 app
docker compose logs --tail=100 postgres
```

## Production Checks

Typical checks on server:

```bash
cd ~/yummydoors_backend
docker compose ps
docker compose logs --tail=100 app
curl -i http://127.0.0.1:8010/health
```

## Important Reality

- A green image build does not guarantee the VPS has recreated the container.
- Verify both the workflow and the running container state.
- Env changes on the server usually require recreating the `app` service.
