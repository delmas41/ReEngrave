#!/bin/bash
# The shape-frequency tie-break on the two other works whose read pass is
# already committed. Both are Litolff, which labels winds and brass on every
# system and the strings on none — so their movement OPENING carries strictly
# more labels than any other system and the tie the Brahms 4 arm turns on does
# not arise. The control is that it does not arise: a change that only fires
# on a tie must be shown not to fire where there is none.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-lineup-swap-2026-09/out
export OMR_SURYA_KEEP_ALIVE=0
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/editions

mkdir -p "$OUT/beet6" "$OUT/beet5"
python3 -u benchmarks/omr-lineup-swap-2026-09/probe/compose_shapetie.py \
    "$LIB/beethoven/symphony-6-op68/beethoven--symphony-6-op68--henry-litolff-s-verlag-1870--imslp504082.pdf" \
    --out-dir "$OUT/beet6" --pages 0-78 --dpi 600 \
    --cache benchmarks/omr-span-reach-2026-09/out/beet6/cache600 \
    --veto report --tag=shapetie
python3 -u benchmarks/omr-lineup-swap-2026-09/probe/compose_shapetie.py \
    "$LIB/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf" \
    --out-dir "$OUT/beet5" --pages 0-87 --dpi 600 \
    --cache benchmarks/omr-slot-alignment-2026-09/out/cache-beet5 \
    --veto report --tag=shapetie
echo "SHAPETIE CONTROLS DONE"
