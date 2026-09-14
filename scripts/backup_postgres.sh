#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# CortexHeal — PostgreSQL Backup Script
# ═══════════════════════════════════════════════════════════
# Writes a timestamped pg_dump to /opt/cortexheal/backups/.
# Safe to run from a host crontab entry.
#
# Usage:
#   sudo bash /opt/cortexheal/repo/scripts/backup_postgres.sh
#
# Crontab example (daily at 03:00):
#   0 3 * * * /opt/cortexheal/repo/scripts/backup_postgres.sh >> /opt/cortexheal/backups/backup.log 2>&1
# ═══════════════════════════════════════════════════════════

set -euo pipefail

BACKUP_DIR="/opt/cortexheal/backups"
CONTAINER_NAME="cortexheal-postgres-1"  # default compose service name
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DUMP_FILE="${BACKUP_DIR}/cortexheal_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Starting backup..."

# Run pg_dump inside the running Postgres container and gzip on the host
docker exec "${CONTAINER_NAME}" \
  pg_dump -U cortexheal -d cortexheal_db --no-owner --no-privileges \
  | gzip > "${DUMP_FILE}"

DUMP_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
echo "[$(date -Iseconds)] Backup complete: ${DUMP_FILE} (${DUMP_SIZE})"

# Prune old backups beyond retention window
DELETED=$(find "${BACKUP_DIR}" -name "cortexheal_db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "[$(date -Iseconds)] Pruned ${DELETED} backups older than ${RETENTION_DAYS} days."
