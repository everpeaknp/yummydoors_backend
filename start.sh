#!/bin/bash
# ./start.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APP_HOST="${YUMMYDOORS_APP_HOST:-127.0.0.1}"
APP_PORT="${YUMMYDOORS_APP_PORT:-8000}"
VENV_DIR="${YUMMYDOORS_VENV_DIR:-.venv}"

if [ ! -f .env ]; then
    echo "ERROR: Missing .env file. Create it from .env.example first."
    exit 1
fi

# Extract variables safely for startup display.
DATABASE_URL="$(grep '^YUMMYDOORS_DATABASE_URL=' .env | cut -d'=' -f2- || true)"
APP_ENV_VALUE="$(grep '^YUMMYDOORS_APP_ENV=' .env | cut -d'=' -f2- || true)"
DEBUG_VALUE="$(grep '^YUMMYDOORS_DEBUG=' .env | cut -d'=' -f2- || true)"

echo "========================================"
echo "     YUMMYDOORS BACKEND STARTUP         "
echo "========================================"

if [ -n "$DATABASE_URL" ]; then
    DB_HOST="$(echo "$DATABASE_URL" | sed -e 's/.*@//' -e 's/:.*//' -e 's/\/.*//')"
    echo "DATABASE: $DATABASE_URL"
    echo "HOST:     $DB_HOST"
else
    echo "DATABASE: Not found in .env"
    DB_HOST="unknown"
fi

echo "ENV:      ${APP_ENV_VALUE:-unknown}"
echo "DEBUG:    ${DEBUG_VALUE:-unknown}"
echo "SERVER:   http://$APP_HOST:$APP_PORT"

if [[ "$DATABASE_URL" == *"azure.com"* ]] || [[ "$DATABASE_URL" == *"supabase.co"* ]] || [[ "$DATABASE_URL" == *"render.com"* ]]; then
    echo ""
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "WARNING: CONNECTING TO NON-LOCAL DB"
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "Target: $DB_HOST"
    echo "If this is unintended, stop now (CTRL+C)."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo ""
    sleep 3
else
    echo "MODE:     LOCAL DEVELOPMENT"
fi

echo "========================================"
echo ""

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Create it with: python3 -m venv $VENV_DIR && $VENV_DIR/bin/pip install -e ."
    exit 1
fi

if command -v docker >/dev/null 2>&1; then
    echo "Ensuring local PostgreSQL container is running..."
    docker compose up -d >/dev/null
fi

# Kill existing process on configured port, matching yummy_backend behavior.
if command -v lsof >/dev/null 2>&1; then
    EXISTING_PID="$(lsof -t -i:"$APP_PORT" || true)"
    if [ -n "$EXISTING_PID" ]; then
        echo "Port $APP_PORT in use. Cleaning up process $EXISTING_PID..."
        kill -9 "$EXISTING_PID" 2>/dev/null || true
        sleep 1
    fi
fi

export PYTHONPATH="${PYTHONPATH:-}:."
source "$VENV_DIR/bin/activate"

echo "Verifying database state..."
if ! python -m alembic upgrade head; then
    echo "ERROR: Failed to run Alembic migrations"
    exit 1
fi

echo "Starting FastAPI server on http://$APP_HOST:$APP_PORT"
echo "API Docs: http://$APP_HOST:$APP_PORT/docs"
echo ""

python -m uvicorn app.main:app \
    --reload \
    --reload-exclude '.venv/*' \
    --reload-exclude 'venv/*' \
    --host "$APP_HOST" \
    --port "$APP_PORT"
