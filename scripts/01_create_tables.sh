#!/usr/bin/env bash
set -euo pipefail

# Ir a la raíz del repo (este script vive en scripts/)
cd "$(dirname "$0")/.."

# 1) Cargar .env y EXPORTAR variables (para que docker run las vea si hiciera falta)
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "❌ No se encontró .env. Copiá .env.example a .env y ajustá credenciales."
  exit 1
fi

# 2) Parámetros
CONTAINER_NAME="${CONTAINER_NAME:-ev-postgres}"     # opcional, solo para chequeo de health
IMAGE_TAG="${IMAGE_TAG:-postgres:12.7}"
SCHEMA_PATH="${SCHEMA_PATH:-$(pwd)/db/schema.sql}"

# Host del Postgres dentro de la red de docker compose:
# por defecto 'db' (nombre del servicio en docker-compose). Se puede overridear en .env
DB_HOST="${DB_HOST:-db}"

# 3) Validaciones básicas
if [ ! -f "$SCHEMA_PATH" ]; then
  echo "❌ No existe $SCHEMA_PATH"
  exit 1
fi

if [ -z "${POSTGRES_DB:-}" ] || [ -z "${POSTGRES_USER:-}" ] || [ -z "${POSTGRES_PASSWORD:-}" ]; then
  echo "❌ Variables requeridas vacías. Verificá .env:"
  echo "   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD (y opcional DB_HOST)"
  exit 1
fi

# 4) Verificar que el contenedor esté healthy (si existe)
echo "⏳ Verificando estado del contenedor ${CONTAINER_NAME}..."
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}\$"; then
  # El contenedor existe: esperamos a healthy
  until [ "$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null || echo "unknown")" = "healthy" ]; do
    echo "   Esperando a ${CONTAINER_NAME} (levántalo con: docker compose up -d si aún no está corriendo)..."
    sleep 2
  done
else
  # No existe (puede que no uses container_name). Al menos sugerimos levantar compose.
  echo "⚠️  No se encontró el contenedor ${CONTAINER_NAME}."
  echo "   Asegurate de tener la DB levantada con: docker compose up -d"
fi

# 5) Detectar la red _default del proyecto (para conectar el contenedor efímero)
NETWORK="$(docker network ls --format '{{.Name}}' | grep '_default$' | head -n1 || true)"
if [ -z "$NETWORK" ]; then
  echo "❌ No se pudo detectar la red de docker compose (_default)."
  echo "   Corré 'docker network ls' y usá el nombre correcto con --network."
  exit 1
fi

# 6) Info de depuración
echo "🔧 Parámetros:"
echo "   IMAGE_TAG:        $IMAGE_TAG"
echo "   NETWORK:          $NETWORK"
echo "   DB_HOST:          $DB_HOST"
echo "   POSTGRES_DB:      $POSTGRES_DB"
echo "   POSTGRES_USER:    $POSTGRES_USER"
echo "   SCHEMA_PATH:      $SCHEMA_PATH"

# 7) Ejecutar el DDL
#    Usamos expansión en el host (sin bash -lc) para evitar perder variables y que psql intente 'root'.
docker run --rm \
  --network "$NETWORK" \
  -v "$SCHEMA_PATH":/sql/schema.sql:ro \
  -e PGPASSWORD="${POSTGRES_PASSWORD}" \
  "$IMAGE_TAG" \
  psql -h "${DB_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f /sql/schema.sql

echo "✅ Tablas creadas/aseguradas."