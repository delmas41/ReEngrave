#!/bin/bash
# The other half of the 2x2: OMR_SPAN_REFERENCE_FIT=refuse, swap split off/on.
# `search` is the shipped default and is the pair already measured.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-lineup-swap-2026-09/out/brahms4
CACHE=benchmarks/omr-span-reach-2026-09/out/brahms4/cache600
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-4-op98/brahms--symphony-4-op98--breitkopf-hartel-brahms--imslp317596.pdf
export OMR_SURYA_KEEP_ALIVE=0
export OMR_SPAN_REFERENCE_FIT=refuse
for arm in 0 1; do
    OMR_LINEUP_SWAP_SPLIT=$arm python3 -u \
        benchmarks/omr-lineup-swap-2026-09/probe/compose_swap.py "$PDF" \
        --out-dir "$OUT" --pages 0-98 --dpi 600 --cache "$CACHE" \
        --veto report --tag="refuse-swap$arm"
done
echo "REFUSE AB DONE"
