#!/bin/bash
# A SECOND whole work through the composition harness, unchanged.
#
# Brahms 1 / Breitkopf is the right second work for this question: like
# Beethoven 5 its finale ADDS instruments (contrabassoon, trombones) that the
# earlier movements do not contain, so a whole-document reference is again the
# finale's lineup and the same bug has room to occur.
#
# OMR_SURYA_KEEP_ALIVE=0 on purpose: this run must own its own margin-reader
# worker rather than depend on the machine's shared keep-alive server, which
# another session owns and which this run is not allowed to repair.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
exec python3 -u benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
    /Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
    --out-dir "$OUT" --pages 0-85 --dpi 600 \
    --cache "$OUT/cache600" --veto report
