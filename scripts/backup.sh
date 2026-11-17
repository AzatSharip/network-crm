#!/usr/bin/env bash
# Run on the deployment host with ENV_FILE, BACKUP_DIR and AGE_RECIPIENT set.
set -euo pipefail
umask 077
: "${ENV_FILE:?absolute path outside repository}"
: "${BACKUP_DIR:?absolute path outside repository}"
: "${AGE_RECIPIENT:?age public recipient}"
command -v age >/dev/null
repo=$(cd "$(dirname "$0")/.." && pwd)
case "$BACKUP_DIR" in "$repo"|"$repo"/*) echo 'Backup destination must be outside repository' >&2; exit 1;; esac
[[ "$BACKUP_DIR" = /* ]] || { echo 'Absolute BACKUP_DIR required' >&2; exit 1; }
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
file="$BACKUP_DIR/network-crm-$(date -u +%Y%m%dT%H%M%SZ)-$$.dump.age"
partial="$file.partial"
trap 'rm -f "$partial"' EXIT
if docker compose version >/dev/null 2>&1; then compose=(docker compose); else compose=(docker-compose); fi
"${compose[@]}" --env-file "$ENV_FILE" -f "$repo/compose.yaml" exec -T db pg_dump -U crm_migrator -d network_crm -Fc --no-owner | age -r "$AGE_RECIPIENT" -o "$partial"
test -s "$partial"
mv "$partial" "$file"
# No automatic deletion of archives. Retention happens only after a restore-verified receipt.
printf '%s\n' "$file"
