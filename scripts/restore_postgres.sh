#!/usr/bin/env sh
set -eu

BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 backups/telegram_learning_bot_YYYYmmdd_HHMMSS.dump" >&2
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

DB_USER="${POSTGRES_USER:-bot_user}"
DB_NAME="${POSTGRES_DB:-telegram_learning_bot}"
DB_CONTAINER="${POSTGRES_CONTAINER:-postgres}"

echo "Restoring $BACKUP_FILE into database $DB_NAME..."
docker compose exec -T "$DB_CONTAINER" pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --username "$DB_USER" \
  --dbname "$DB_NAME" < "$BACKUP_FILE"

echo "Restore completed."
