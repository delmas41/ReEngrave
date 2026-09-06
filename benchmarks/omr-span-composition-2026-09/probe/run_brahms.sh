#!/bin/bash
# Brahms 1 / Breitkopf, three `OMR_SPAN_REFERENCE_FIT` arms off ONE shared read
# pass (the veto-pricing session's committed cache: the margin read, which is
# flag-independent by construction, so every difference below is this flag).
#
# `off` reproduces the pre-2026-09-06 behaviour and MUST land on the recorded
# 36 / 14 / 149 / 133 — that is the harness assertion, not a result.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600
OUT=benchmarks/omr-span-composition-2026-09/out/brahms1
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
for ARM in off refuse search; do
  echo "=== ARM $ARM  $(date -u +%FT%TZ)"
  OMR_SPAN_REFERENCE_FIT=$ARM python3 -u \
    benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py "$PDF" \
    --out-dir "$OUT" --pages 0-85 --dpi 600 --cache "$CACHE" --veto report \
    --tag="-fit$ARM" 2>&1 | tail -4
done
echo "=== SCORING $(date -u +%FT%TZ)"
python3 benchmarks/omr-span-composition-2026-09/probe/score_brahms.py \
  "fit-off=$OUT/-fitoff" "fit-refuse=$OUT/-fitrefuse" "fit-search=$OUT/-fitsearch"
echo "=== DONE $(date -u +%FT%TZ)"
