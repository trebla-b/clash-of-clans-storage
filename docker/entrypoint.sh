#!/bin/sh
set -eu

CRON_EXPR="$(python -m app.print_cron)"
CRON_FILE="/etc/crontabs/root"

printf '%s\n' "${CRON_EXPR} cd /app && python -m app.fetch_once >> /proc/1/fd/1 2>> /proc/1/fd/2" > "${CRON_FILE}"

echo "[cron] schedule=${CRON_EXPR}"
python -m app.fetch_once || true

exec crond -f -l 2
