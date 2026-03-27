#!/bin/sh
set -eu

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-coc}"
POSTGRES_USER="${POSTGRES_USER:-coc}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-21600}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-28}"

mkdir -p "${BACKUP_DIR}"

log() {
  printf '[db-backup] %s\n' "$*"
}

wait_for_db() {
  until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
    log "waiting for postgres ${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
    sleep 2
  done
}

prune_backups() {
  files="$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name "${POSTGRES_DB}"_*.sql.gz | LC_ALL=C sort || true)"
  [ -n "${files}" ] || return 0

  count="$(printf '%s\n' "${files}" | wc -l | tr -d ' ')"
  if [ "${count}" -le "${BACKUP_RETENTION_COUNT}" ]; then
    return 0
  fi

  remove_count=$((count - BACKUP_RETENTION_COUNT))
  printf '%s\n' "${files}" | head -n "${remove_count}" | while IFS= read -r file; do
    [ -n "${file}" ] || continue
    rm -f "${file}"
    log "removed old backup $(basename "${file}")"
  done
}

create_backup() {
  timestamp="$(date -u +"%Y%m%dT%H%M%SZ")"
  tmp_file="${BACKUP_DIR}/.${POSTGRES_DB}_${timestamp}.sql.gz.tmp"
  final_file="${BACKUP_DIR}/${POSTGRES_DB}_${timestamp}.sql.gz"

  log "creating backup $(basename "${final_file}")"
  pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges | gzip -9 > "${tmp_file}"

  mv "${tmp_file}" "${final_file}"
  log "backup stored at ${final_file}"
  prune_backups
}

log "interval=${BACKUP_INTERVAL_SECONDS}s retention=${BACKUP_RETENTION_COUNT} backup_dir=${BACKUP_DIR}"
wait_for_db
create_backup

while true; do
  sleep "${BACKUP_INTERVAL_SECONDS}"
  wait_for_db
  create_backup
done
