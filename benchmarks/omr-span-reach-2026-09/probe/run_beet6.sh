#!/bin/bash
# The THIRD whole work through the composition harness, unchanged.
#
# Beethoven 6 / Litolff 1870 is the right third work. The phase-1 screen
# (`span_profile.py`) puts it at THREE lineup spans — 0-26, 27-45, 46-78 —
# where both measured works take two, so it is the first document on which
# `_align_by_span` has to compose more than one span reference into the
# document's slot space. Same 1870 Litolff series as Beethoven 5, which is the
# limitation to state rather than hide: it holds the publisher's labelling
# convention fixed and varies the work.
#
# OMR_SURYA_KEEP_ALIVE=0 on purpose: this run owns its own margin-reader
# worker. The machine's shared keep-alive server belongs to other sessions and
# this run is not allowed to repair it.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=benchmarks/omr-span-reach-2026-09/out/beet6
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
exec python3 -u benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
    /Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-6-op68/beethoven--symphony-6-op68--henry-litolff-s-verlag-1870--imslp504082.pdf \
    --out-dir "$OUT" --pages 0-78 --dpi 600 \
    --cache "$OUT/cache600" --veto report
