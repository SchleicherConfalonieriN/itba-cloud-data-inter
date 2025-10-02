#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------
# run_all.sh  —  E2E pipeline
#   1) docker compose up -d (Postgres 12.7)
#   2) crear tablas (DDL)
#   3) build imagen app (Python + scripts)
#   4) cargar datos (loader)
#   5) ejecutar reportes
#
# Flags:
#   --reset        : docker compose down -v (borra datos) y vuelve a subir
#   --skip-build   : no reconstruir imagen app
#   --skip-load    : no correr loader
#   --skip-reports : no correr reportes
# -----------------------------------------------

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

APP_IMAGE="${APP_IMAGE:-itba/app-runner:latest}"
DOCKERFILE="${DOCKERFILE:-app-image/Dockerfile}"
DB_CONTAINER="${DB_CONTAINER:-ev-postgres}"   # debe coincidir con docker-compose.yml
DB_SERVICE_HOST="${DB_SERVICE_HOST:-db}"      # nombre del servicio en compose (host interno)

RESET=0
SKIP_BUILD=0
SKIP_LOAD=0
SKIP_REPORTS=0

for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    --skip-load) SKIP_LOAD=1 ;;
    --skip-reports) SKIP_REPORTS=1 ;;
    *) echo "Unknown flag: $arg"; exit 2 ;;
  esac
done

# -------- Helpers --------
need() { command -v "$1" >/dev/null 2>&1 || { echo "❌ Missing: $1"; exit 1; }; }
ensure_env() {
  if [[ -f ".env" ]]; then
    set -a; # export auto
    # shellcheck disable=SC1091
    source .env
    set +a
  else
    echo "❌ .env not found. Copy .env.example to .env and set credentials."; exit 1
  fi
  : "${POSTGRES_DB:?}"; : "${POSTGRES_USER:?}"; : "${POSTGRES_PASSWORD:?}"
}
detect_network() {
  docker network ls --format '{{.Name}}' | grep '_default$' | head -n1
}
wait_healthy() {
  if docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}\$"; then
    echo "⏳ Waiting for ${DB_CONTAINER} to be healthy..."
    until [ "$(docker inspect -f '{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || echo unknown)" = "healthy" ]; do
      sleep 2
    done
  else
    echo "⚠️  Container ${DB_CONTAINER} not found yet (compose will create it)."
  fi
}

# -------- Checks --------
need docker
ensure_env

# -------- Reset (optional) --------
if [[ "$RESET" -eq 1 ]]; then
  echo "♻️  Resetting DB (down -v) ..."
  docker compose down -v || true
fi

# -------- Up DB --------
echo "🚀 Bringing up Postgres..."
docker compose up -d
wait_healthy

# -------- Create tables (DDL) --------
echo "📐 Creating tables (DDL)..."
chmod +x scripts/01_create_tables.sh
./scripts/01_create_tables.sh

# -------- Build app image --------
if [[ "$SKIP_BUILD" -eq 0 ]]; then
  echo "🧱 Building app image: ${APP_IMAGE}"
  docker build -t "${APP_IMAGE}" -f "${DOCKERFILE}" .
else
  echo "⏭️  Skipping build ( --skip-build )"
fi

# -------- Detect compose default network --------
NETWORK="$(detect_network)"
if [[ -z "$NETWORK" ]]; then
  echo "❌ Could not detect compose default network (_default)."
  echo "   Use: docker network ls   and set NETWORK manually here."
  exit 1
fi
echo "🌐 Using network: ${NETWORK}"

# -------- Load data (optional skip) --------
if [[ "$SKIP_LOAD" -eq 0 ]]; then
  echo "📥 Loading EV dataset into DB..."
  docker run --rm \
    --network "$NETWORK" \
    --env-file ./.env \
    -e EV_DATA_URL="${EV_DATA_URL:-https://data.wa.gov/api/views/f6w7-q2d2/rows.json?accessType=DOWNLOAD}" \
    "${APP_IMAGE}" \
    /app/scripts/02_load_data.py
else
  echo "⏭️  Skipping loader ( --skip-load )"
fi

# -------- Reports (optional skip) --------
if [[ "$SKIP_REPORTS" -eq 0 ]]; then
  echo "📊 Running reports..."
  docker run --rm \
    --network "$NETWORK" \
    --env-file ./.env \
    -e PYTHONUNBUFFERED=1 \
    "${APP_IMAGE}" \
    /app/scripts/03_run_reports.py
else
  echo "⏭️  Skipping reports ( --skip-reports )"
fi

echo "✅ Done."