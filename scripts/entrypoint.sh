#!/bin/bash

set -euo pipefail

DB_HOST="${YUMMYDOORS_POSTGRES_HOST:-postgres}"
DB_PORT="${YUMMYDOORS_POSTGRES_PORT:-5432}"
DB_NAME="${YUMMYDOORS_POSTGRES_DB:-yummydoors}"
DB_USER="${YUMMYDOORS_POSTGRES_USER:-postgres}"
APP_PORT="${PORT:-8080}"

echo "========================================"
echo "   YUMMYDOORS PRODUCTION CONTAINER      "
echo "========================================"
echo "APP_ENV:   ${YUMMYDOORS_APP_ENV:-unknown}"
echo "DB_HOST:   $DB_HOST"
echo "DB_PORT:   $DB_PORT"
echo "DB_NAME:   $DB_NAME"
echo "APP_PORT:  $APP_PORT"
echo "========================================"

echo "Waiting for PostgreSQL..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  sleep 2
done

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Running Alembic migrations..."
  python -m alembic upgrade heads
fi

echo "Starting Gunicorn..."
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind "0.0.0.0:${APP_PORT}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT:-30}" \
  --keep-alive "${GUNICORN_KEEPALIVE:-5}" \
  --access-logfile - \
  --error-logfile -
