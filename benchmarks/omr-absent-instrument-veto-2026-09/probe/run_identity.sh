#!/bin/bash
# Identity layer only, no detector. $1 = tag, $2 = pdf, $3 = optional --pages spec
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="$(cd "$BENCH/../.." && pwd)"
TAG="$1"; PDF="$2"; PAGES="${3:-}"
export OMR_ABSENT_INSTRUMENT_VETO=report
export OMR_SURYA_KEEP_ALIVE=1
export PYTHONUNBUFFERED=1
cd "$ROOT" || exit 1
ARGS=("$BENCH/probe/identity_only.py" "$PDF" "$BENCH/out/$TAG.json")
[ -n "$PAGES" ] && ARGS+=("--pages=$PAGES")
echo "=== $TAG start $(date -u +%FT%TZ)" > "$BENCH/out/$TAG.log"
S=$(date +%s)
nice -n 10 python3 "${ARGS[@]}" >>"$BENCH/out/$TAG.log" 2>&1
echo "=== $TAG rc=$? wall=$(( $(date +%s) - S ))s" >> "$BENCH/out/$TAG.log"
