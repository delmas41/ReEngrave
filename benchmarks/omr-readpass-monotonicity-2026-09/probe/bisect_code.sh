#!/bin/bash
# Which COMMIT flips Beethoven 5 slot 8 from Timpani to Trumpet?
#
# The label set is held fixed (one cached read pass, byte-identical staves and
# byte-identical margin labels for every arm), so a difference between two rows
# of this output is code and nothing else.  Each arm costs ~5 s.
#
#     bisect_code.sh SHA [SHA ...]
#
# ⚠️ Restores `tools/omr` to the branch head on exit, including on interrupt.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
CACHE=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a28a9beefa2dbc9f7/benchmarks/omr-slot-alignment-2026-09/out/cache-beet5
OUT=benchmarks/omr-readpass-monotonicity-2026-09/out/bisect
RUN=benchmarks/omr-readpass-monotonicity-2026-09/probe/run_labelsets.py
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0

restore() { git checkout -- tools/omr 2>/dev/null; git reset -q 2>/dev/null; }
trap restore EXIT INT TERM

for SHA in "$@"; do
  git checkout "$SHA" -- tools/omr 2>/dev/null || { echo "$SHA CHECKOUT-FAILED"; continue; }
  python3 -u "$RUN" "$PDF" --cache "$CACHE" --out-dir "$OUT" --tag="$SHA" \
      >"$OUT/$SHA.log" 2>&1
  RC=$?
  SLOT8=$(python3 - "$OUT/$SHA.json" <<'PY' 2>/dev/null
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print("NO-OUTPUT"); raise SystemExit
ref = {s["slot"]: s["instrument"] for s in d["contextual"]["reference"]}
si = {s["slot"]: (s["instrument"], s.get("source"))
      for s in d["contextual"]["absent_instrument_veto"]["slot_instruments"]}
print(f'slot8={ref.get(8)} src={si.get(8, ("?", "?"))[1]} n_ref={len(ref)}')
PY
)
  SUBJ=$(git log -1 --pretty='%ad %s' --date=short "$SHA")
  echo "$SHA rc=$RC $SLOT8 | $SUBJ"
  restore
done
