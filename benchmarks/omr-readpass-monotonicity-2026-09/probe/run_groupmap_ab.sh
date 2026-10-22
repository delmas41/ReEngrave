#!/bin/bash
# Does the group-map flag measure the same thing with and without CLEFS?
#
# Every arm in the phase-0 identity harness is a clef-blind replay.  If a flag's
# measured effect differs once the clefs the real pipeline has are supplied,
# then the harness's gate is grading a configuration the pipeline never runs.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a28a9beefa2dbc9f7/benchmarks/omr-slot-alignment-2026-09/out/cache-beet5
OUT=benchmarks/omr-readpass-monotonicity-2026-09/out
RUN=benchmarks/omr-readpass-monotonicity-2026-09/probe/run_labelsets.py
CLEFS=$OUT/passA-clefs.json
export OMR_SURYA_KEEP_ALIVE=0
for ARM in ordinal map; do
  OMR_SLOT_GROUP_MAP=$ARM python3 -u "$RUN" "$PDF" --cache "$CACHE" \
      --out-dir "$OUT" --tag="arm-groupmap-$ARM-noclefs" >/dev/null 2>&1
  OMR_SLOT_GROUP_MAP=$ARM python3 -u "$RUN" "$PDF" --cache "$CACHE" \
      --out-dir "$OUT" --tag="arm-groupmap-$ARM-clefs" --clefs "$CLEFS" \
      >/dev/null 2>&1
done
python3 benchmarks/omr-readpass-monotonicity-2026-09/probe/score_arms.py beet5 \
    "$OUT/arm-groupmap-ordinal-noclefs.json" "$OUT/arm-groupmap-map-noclefs.json" \
    "$OUT/arm-groupmap-ordinal-clefs.json" "$OUT/arm-groupmap-map-clefs.json" \
    | sed -n '1,6p'
