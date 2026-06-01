#!/usr/bin/env sh
set -eu

if [ "$#" -eq 0 ] || [ "$1" = "serve" ]; then
  if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "Running database migrations"
    alembic upgrade head
  fi

  set -- uvicorn main:app --host 0.0.0.0 --port "${PORT:-5003}"
fi

exec "$@"
