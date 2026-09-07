#!/bin/bash
# One controlled A/B: the SAME page, the same tree, the same flags apart from
# OMR_ONE_LINE_STAVES. Both arms run serially so neither is measured under a
# different machine load than the other.
#
#   run_ab.sh <tag> <pdf> <page-index> [extra transcribe args...]
#
# Writes $SCRATCH/<tag>_off.json and $SCRATCH/<tag>_on.json.
set -u
TAG="$1"; PDF="$2"; PAGE="$3"; shift 3
: "${SCRATCH:?set SCRATCH to a writable directory}"
export OMR_SURYA_KEEP_ALIVE=0   # an unattended run must own its own worker

for ARM in off on; do
  OUT="$SCRATCH/${TAG}_${ARM}.json"
  if [ -f "$OUT" ]; then echo "have $OUT"; continue; fi
  if [ "$ARM" = on ]; then export OMR_ONE_LINE_STAVES=1
  else unset OMR_ONE_LINE_STAVES; fi
  echo "=== $TAG $ARM ==="
  python3 -u -m tools.omr.transcribe "$PDF" --pages "$PAGE" \
      --out "$OUT" "$@" 2>&1 | tail -6
done
echo "AB_DONE $TAG"
