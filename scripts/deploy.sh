#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: Missing $ENV_FILE"
  echo "Create it from .env.production.example before deploying."
  exit 1
fi

echo "Validating Docker Compose configuration..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" config >/dev/null

echo "Pulling base images..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull postgres || true

echo "Backing up active production env file..."
cp "$ENV_FILE" "${ENV_FILE}.bak"

echo "Building and starting YummyDoors backend..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build --force-recreate --remove-orphans

echo "Current container status:"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

echo "Recent app logs:"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=60 app
