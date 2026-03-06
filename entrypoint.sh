#!/bin/sh
set -e

echo "Waiting for postgres..."

until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

echo "Running migrations..."
uv run alembic upgrade head

echo "Starting bot..."
exec "$@"