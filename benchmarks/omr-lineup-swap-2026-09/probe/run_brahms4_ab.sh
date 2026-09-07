#!/bin/bash
# The identity A/B for the swap split, off ONE warm read cache.
#
# ⚠️ Two arms, two --tag values (with `=`), so neither can silently reuse the
# other's transcriptions — the cached-A/B trap. compose.py caches only the READ
# pass, which is the shared control; the contextual pass runs per arm.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-lineup-swap-2026-09/out/brahms4
CACHE=benchmarks/omr-span-reach-2026-09/out/brahms4/cache600
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-4-op98/brahms--symphony-4-op98--breitkopf-hartel-brahms--imslp317596.pdf
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0

for arm in 0 1; do
    OMR_LINEUP_SWAP_SPLIT=$arm python3 -u \
        benchmarks/omr-lineup-swap-2026-09/probe/compose_swap.py "$PDF" \
        --out-dir "$OUT" --pages 0-98 --dpi 600 --cache "$CACHE" \
        --veto report --tag="swap$arm"
done
echo "BRAHMS4 AB DONE"
