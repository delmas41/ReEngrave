#!/bin/bash
# A FOURTH work, and the first that varies the publisher within a family that
# has already been measured: Brahms 4 / Breitkopf takes two spans (boundary 41)
# like Brahms 1 / Breitkopf, so it asks whether the composition fix that
# repaired Brahms 1 repairs its sibling, or was fitted to it.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-span-reach-2026-09/out/brahms4
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
exec python3 -u benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
    /Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-4-op98/brahms--symphony-4-op98--breitkopf-hartel-brahms--imslp317596.pdf \
    --out-dir "$OUT" --pages 0-98 --dpi 600 \
    --cache "$OUT/cache600" --veto report
