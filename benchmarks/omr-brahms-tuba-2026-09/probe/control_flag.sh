#!/bin/bash
# CONTROL: flag off, and flag ON with no roster supplier, are both no-ops.
#
# The second is the one worth checking. `work_roster.py` is on a sibling branch
# and not in this tree, so the wiring's import fails, `admissible` is None, and
# `find_offroster_vetoes` abstains — which is exactly the shape of a change
# that LOOKS live and is not. Both arms are compared byte for byte against the
# committed shipped run.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600
OUT=benchmarks/omr-brahms-tuba-2026-09/out/control
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
for ARM in off on; do
  echo "=== OMR_ROSTER_SCORE_ORDER_VETO=$ARM  $(date -u +%FT%TZ)"
  OMR_ROSTER_SCORE_ORDER_VETO=$ARM python3 -u \
      benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py \
      "$PDF" --out-dir "$OUT" --pages 0-85 --dpi 600 --cache "$CACHE" \
      --veto report --tag="-flag$ARM" 2>&1 | grep -E "^\[|wrote|read "
done
echo "=== DONE $(date -u +%FT%TZ)"
for ARM in off on; do
  for S in off on; do
    A="$OUT/-flag$ARM-spans-$S.json"
    B="benchmarks/omr-brahms-tuba-2026-09/out/run/-shipped-spans-$S.json"
    if cmp -s "$A" "$B"; then
      echo "  BYTE-IDENTICAL  flag=$ARM spans=$S"
    else
      echo "  DIFFERS         flag=$ARM spans=$S"
    fi
  done
done
