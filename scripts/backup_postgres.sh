#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-backups}"
POSTGRES_DB="${POSTGRES_DB:-telegram_learning_bot}"
POSTGRES_USER="${POSTGRES_USER:-bot_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-bot_password}"
POSTGRES_HOST="${POSTGRES_HOST:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="$BACKUP_DIR/${POSTGRES_DB}_${timestamp}.dump"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --host="$POSTGRES_HOST" \
  --port="$POSTGRES_PORT" \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --format=custom \
  --no-owner \
  --file="$backup_path"

echo "Backup saved to $backup_path"
