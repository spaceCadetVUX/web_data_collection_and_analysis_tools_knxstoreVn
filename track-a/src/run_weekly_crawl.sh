#!/bin/bash
# Weekly crawl KNX + CSA Matter -> import vào Postgres dev. Chạy qua launchd (xem
# com.knxstore.registry-weekly-crawl.plist). Mỗi bước log ra file riêng theo lần chạy
# để không "chết âm thầm" — n8n digest (A5) query registry.crawl_log để biết crawl có
# ok hay không trước khi gửi tin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

set -a
source .env
set +a

DB_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"

LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/weekly_crawl_$(date +%Y%m%d_%H%M%S).log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "=== Weekly crawl start ==="

log "--- KNX crawl ---"
if python3 crawl_knx_devices.py --output ../data/_weekly_knx.csv >>"$LOG_FILE" 2>&1; then
  log "KNX crawl OK"
  if python3 import_and_diff.py --db-url "$DB_URL" --csv ../data/_weekly_knx.csv --registry-key knx >>"$LOG_FILE" 2>&1; then
    log "KNX import OK"
  else
    log "KNX import FAILED — xem $LOG_FILE"
  fi
else
  log "KNX crawl FAILED — bỏ qua import, xem $LOG_FILE"
fi

log "--- Matter crawl ---"
if python3 crawl_matter_devices.py --output ../data/_weekly_matter.csv >>"$LOG_FILE" 2>&1; then
  log "Matter crawl OK"
  if python3 import_and_diff.py --db-url "$DB_URL" --csv ../data/_weekly_matter.csv --registry-key matter_csa >>"$LOG_FILE" 2>&1; then
    log "Matter import OK"
  else
    log "Matter import FAILED — xem $LOG_FILE"
  fi
else
  log "Matter crawl FAILED — bỏ qua import, xem $LOG_FILE"
fi

log "=== Weekly crawl end ==="
