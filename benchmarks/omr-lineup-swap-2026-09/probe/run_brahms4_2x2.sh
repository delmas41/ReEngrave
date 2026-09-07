#!/bin/bash
# The 2x2: reference tie-break {document order, shape frequency} x swap split
# {off, on}, off the one warm read cache.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-lineup-swap-2026-09/out/brahms4
CACHE=benchmarks/omr-span-reach-2026-09/out/brahms4/cache600
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-4-op98/brahms--symphony-4-op98--breitkopf-hartel-brahms--imslp317596.pdf
export OMR_SURYA_KEEP_ALIVE=0
for arm in 0 1; do
  OMR_LINEUP_SWAP_SPLIT=$arm python3 -u \
      benchmarks/omr-lineup-swap-2026-09/probe/compose_shapetie.py "$PDF" \
      --out-dir "$OUT" --pages 0-98 --dpi 600 --cache "$CACHE" \
      --veto report --tag="shapetie-swap$arm"
done
echo "2x2 DONE"
