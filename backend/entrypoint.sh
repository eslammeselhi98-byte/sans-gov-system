#!/usr/bin/env bash
set -euo pipefail

# Ensure uploads/backups exist and have correct permissions
mkdir -p ${UPLOAD_DIR:-/app/uploads} ${BACKUP_DIR:-/app/backups} ${LOG_DIR:-/app/logs}
chown -R $(id -u):$(id -g) ${UPLOAD_DIR:-/app/uploads} ${BACKUP_DIR:-/app/backups} ${LOG_DIR:-/app/logs} || true

# If running in development with sqlite, ensure DB file exists
if [[ "${DATABASE_URL:-}" == sqlite* ]]; then
  DBFILE=$(echo "${DATABASE_URL}" | sed -E 's@sqlite\+aiosqlite:///@@; s@sqlite:///@@')
  if [ -n "$DBFILE" ]; then
    mkdir -p "$(dirname "$DBFILE")"
    touch "$DBFILE" || true
  fi
fi

# Run database migrations if Alembic is available and not using SQLite
DATABASE_MIGRATION_URL="${DATABASE_SYNC_URL:-${DATABASE_URL:-}}"
if command -v alembic >/dev/null 2>&1 && [[ "$DATABASE_MIGRATION_URL" != sqlite* ]]; then
  echo "Running Alembic migrations..."
  alembic upgrade head
fi

exec "$@"
