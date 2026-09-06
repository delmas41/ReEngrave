#!/bin/bash
# One end-to-end transcription arm.  $1 = tag, $2 = pdf, $3 = --pages spec,
# $4 = OMR_REFERENCE_MOST_LABELLED value (off/on/pure).
#
# --no-direction-text throughout: the direction reader is ~75% of wall clock
# and reads WORDS INSIDE the system, which no part of reference selection
# touches. Both arms of every A/B are run the same way, so the comparison is
# unaffected and the runs are affordable.
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$BENCH/../.." && pwd)"
cd "$REPO"
TAG="$1"; PDF="$2"; PAGES="$3"; MODE="$4"
OUT="$BENCH/out/$TAG.json"
LOG="$BENCH/out/$TAG.log"

export OMR_SURYA_KEEP_ALIVE=1
export PYTHONUNBUFFERED=1
export OMR_REFERENCE_MOST_LABELLED="$MODE"

echo "=== $TAG start $(date -u +%FT%TZ)" | tee "$LOG"
echo "pdf=$PDF pages=$PAGES OMR_REFERENCE_MOST_LABELLED=$MODE" | tee -a "$LOG"
START=$(date +%s)
python3 -u -m tools.omr.transcribe "$PDF" --pages "$PAGES" \
    --no-direction-text --out "$OUT" >>"$LOG" 2>&1
RC=$?
echo "=== $TAG rc=$RC wall=$(( $(date +%s) - START ))s" | tee -a "$LOG"
