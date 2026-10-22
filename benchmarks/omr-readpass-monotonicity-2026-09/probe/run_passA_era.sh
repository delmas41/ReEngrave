#!/bin/bash
# THE CLOSING CONTROL: pass A's own code era, pass A's own 962 labels, clefs
# off then on.  If the clef-blind arm reproduces pass B and the clef-bearing arm
# reproduces pass A, then at ONE commit and ONE label set the whole 50-record
# gap is the clefs, and neither the evidence nor the code can be carrying it.
#
# 913a1c5b is the commit closest to when `whole-report2` was transcribed
# (2026-09-06 15:25 UTC); pass A itself ran off the veto session's own branch.
set -u
cd "$(dirname "$0")/../../.." || exit 1
SHA=${1:-913a1c5b}
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a28a9beefa2dbc9f7/benchmarks/omr-slot-alignment-2026-09/out/cache-beet5
OUT=benchmarks/omr-readpass-monotonicity-2026-09/out
RUN=benchmarks/omr-readpass-monotonicity-2026-09/probe/run_labelsets.py
DROP=benchmarks/omr-readpass-monotonicity-2026-09/probe/extra11.json
CLEFS=$OUT/passA-clefs.json
export OMR_SURYA_KEEP_ALIVE=0

restore() { git checkout -- tools/omr 2>/dev/null; git reset -q 2>/dev/null; }
trap restore EXIT INT TERM

git checkout "$SHA" -- tools/omr || exit 1
python3 -u "$RUN" "$PDF" --cache "$CACHE" --out-dir "$OUT" \
    --tag="arm-$SHA-962-noclefs" --drop "$DROP" >"$OUT/era-noclefs.log" 2>&1
python3 -u "$RUN" "$PDF" --cache "$CACHE" --out-dir "$OUT" \
    --tag="arm-$SHA-962-clefs" --drop "$DROP" --clefs "$CLEFS" \
    >"$OUT/era-clefs.log" 2>&1
restore

python3 benchmarks/omr-readpass-monotonicity-2026-09/probe/score_arms.py beet5 \
    "$OUT/arm-$SHA-962-noclefs.json" "$OUT/arm-$SHA-962-clefs.json" \
    benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json \
    | sed -n '1,5p'
