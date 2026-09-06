#!/bin/bash
# Transcribe a page set in report mode. $1 = tag, $2 = pdf, $3 = --pages spec ("" = all)
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BENCH/../.." && pwd)"
TAG="$1"; PDF="$2"; PAGES="${3:-}"; MODE="${4:-report}"
export OMR_SURYA_KEEP_ALIVE=1
export OMR_ABSENT_INSTRUMENT_VETO="$MODE"
export PYTHONUNBUFFERED=1
ARGS=(-u -m tools.omr.transcribe "$PDF" --no-direction-text --out "$BENCH/out/$TAG.json")
[ -n "$PAGES" ] && ARGS+=(--pages "$PAGES")
cd "$ROOT" || exit 1
echo "=== $TAG mode=$MODE pages=${PAGES:-ALL} start $(date -u +%FT%TZ)" | tee "$BENCH/out/$TAG.log"
S=$(date +%s)
nice -n 10 python3 "${ARGS[@]}" >>"$BENCH/out/$TAG.log" 2>&1
RC=$?
echo "=== $TAG rc=$RC wall=$(( $(date +%s) - S ))s" | tee -a "$BENCH/out/$TAG.log"
