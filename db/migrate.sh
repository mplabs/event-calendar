#!/bin/bash
set -euo pipefail

psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "CREATE TABLE IF NOT EXISTS _migrations (name text primary key, applied_at timestamptz default now())"

for f in /migrations/*.sql; do
  name=$(basename "$f")
  if psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
      "SELECT 1 FROM _migrations WHERE name='$name'" | grep -q 1; then
    echo "skip $name (already applied)"
  else
    echo "applying $name"
    psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -f "$f" &&
    psql -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
      -c "INSERT INTO _migrations (name) VALUES ('$name')"
  fi
done
