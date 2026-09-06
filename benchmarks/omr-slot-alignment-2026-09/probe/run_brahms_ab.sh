#!/bin/bash
# Does the group-mapping fix repair the Brahms span regression?
#
# The veto-pricing session measured Brahms 1 pre-finale impossible names at
# 36 spans-off / 149 spans-ON, and traced it to `_align_by_span`'s COMPOSITION
# step -- the span's own 14-slot reference placed into the document's 16-slot
# one, deleting global 6 and 10 instead of 8 and 9. That placement goes through
# `slots.align`, which is the function the bracket-ordinal fix repairs, so this
# asks the question directly.
#
# Re-uses that session's committed read-pass cache: the cache is the margin
# read, which is flag-independent by construction, so both arms see byte-
# identical labels and every difference is OMR_SLOT_GROUP_MAP.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abe066cff5c6c7283/benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/cache600
OUT=benchmarks/omr-slot-alignment-2026-09/out/brahms1
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
for ARM in ordinal map; do
  echo "=== ARM $ARM  $(date -u +%FT%TZ)"
  OMR_SLOT_GROUP_MAP=$ARM python3 -u \
    benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py "$PDF" \
    --out-dir "$OUT" --pages 0-85 --dpi 600 --cache "$CACHE" --veto report \
    --tag="-$ARM" 2>&1 | tail -4
done
echo "=== DONE $(date -u +%FT%TZ)"
