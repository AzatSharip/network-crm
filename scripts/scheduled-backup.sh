#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
file=$("$repo/scripts/backup.sh")
python3 "$repo/scripts/restore-check.py" "$file"
# Pruning remains separate and explicit; default retention report is read-only.
python3 "$repo/scripts/retention.py" "$BACKUP_DIR" --keep 14
