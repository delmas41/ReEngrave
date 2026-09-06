#!/bin/bash
# Transcribe a whole document in ONE run, the way Sean actually uses it.
# $1 = tag, $2 = absolute pdf path, $3 = optional --pages spec
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
TAG="$1"; PDF="$2"; PAGES="${3:-}"
OUT="$BENCH/out/$TAG.json"
LOG="$BENCH/out/$TAG.log"

export OMR_SURYA_KEEP_ALIVE=1
export PYTHONUNBUFFERED=1

ARGS=(-u -m tools.omr.transcribe "$PDF" --out "$OUT")
if [ -n "$PAGES" ]; then ARGS+=(--pages "$PAGES"); fi

echo "=== $TAG start $(date -u +%FT%TZ)" | tee "$LOG"
echo "pdf: $PDF" | tee -a "$LOG"
echo "pages: ${PAGES:-ALL}" | tee -a "$LOG"
START=$(date +%s)
/usr/bin/time -l python3 "${ARGS[@]}" >>"$LOG" 2>&1
RC=$?
END=$(date +%s)
echo "=== $TAG rc=$RC wall=$((END-START))s $(date -u +%FT%TZ)" | tee -a "$LOG"
