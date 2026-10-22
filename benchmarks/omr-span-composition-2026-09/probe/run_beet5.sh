#!/bin/bash
# THE CONTROL. Beethoven 5 / Litolff is the work the whole spans design was
# built on and is currently, spans-on, 0 impossible / 756 correct / 51 wrong of
# 807 judgeable. A fix tuned on Brahms that costs Beethoven is not a fix.
#
# Three `OMR_SPAN_REFERENCE_FIT` arms off the committed read-pass cache.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
CACHE=benchmarks/omr-slot-alignment-2026-09/out/cache-beet5
OUT=benchmarks/omr-span-composition-2026-09/out/beet5
COMPOSE=benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py
SCORE=benchmarks/omr-spans-veto-composition-2026-09/probe/score_2x2.py
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
for ARM in off refuse search; do
  echo "=== ARM $ARM  $(date -u +%FT%TZ)"
  OMR_SPAN_REFERENCE_FIT=$ARM python3 -u "$COMPOSE" "$PDF" \
    --out-dir "$OUT" --pages 0-87 --dpi 600 --cache "$CACHE" --veto report \
    --tag="-fit$ARM" 2>&1 | tail -3
done
for ARM in off refuse search; do
  echo
  echo "############ OMR_SPAN_REFERENCE_FIT=$ARM"
  python3 "$SCORE" "$OUT/-fit$ARM-spans-off.json" "$OUT/-fit$ARM-spans-on.json" \
    2>&1 | sed -n '1,30p'
done
echo "=== DONE $(date -u +%FT%TZ)"
