#!/usr/bin/env bash
# HMS database backup — FRD §9: automated daily encrypted backups, one copy
# off-site, quarterly restore drills (see docs/backup-restore.md).
#
# Usage:  ./scripts/backup.sh
# Cron:   0 2 * * *  cd /path/to/hms && ./scripts/backup.sh >> backups/backup.log 2>&1
#
# Env (or .env at repo root):
#   BACKUP_DIR              target directory        (default ./backups)
#   BACKUP_RETENTION_DAYS   local retention         (default 14)
#   BACKUP_GPG_RECIPIENT    if set, encrypt with GPG public key (recommended)

set -euo pipefail

cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/hms_${STAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u +%FT%TZ)] Starting backup -> ${OUT}"
docker compose exec -T db pg_dump -U hms -d hms --no-owner | gzip > "${OUT}"

if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
  gpg --batch --yes --encrypt --recipient "${BACKUP_GPG_RECIPIENT}" "${OUT}"
  rm "${OUT}"
  OUT="${OUT}.gpg"
fi

# Refuse to accept an implausibly small dump (empty DB / failed pipe)
SIZE=$(wc -c < "${OUT}")
if [ "${SIZE}" -lt 1024 ]; then
  echo "ERROR: backup is ${SIZE} bytes — something is wrong. Keeping file for inspection." >&2
  exit 1
fi

echo "[$(date -u +%FT%TZ)] Backup complete (${SIZE} bytes)."

# Retention: prune old local backups
find "${BACKUP_DIR}" -name "hms_*.sql.gz*" -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -u +%FT%TZ)] Retention applied (${RETENTION_DAYS} days)."
echo "REMINDER: sync ${BACKUP_DIR} off-site (rclone/rsync) — a backup on the same disk is not a backup."
