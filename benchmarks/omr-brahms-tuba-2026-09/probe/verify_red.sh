#!/bin/bash
# Every test in test_offroster_name.py, verified RED by breaking the mechanism
# it guards. A test that passes both ways guards nothing — this repo has one
# recorded (`benchmarks/omr-margin-labels-blob-2026-09`: a regression test that
# asserted on label LENGTH and passed vacuously either way).
#
# Each break is applied to a COPY of the tree, run, and thrown away.
set -u
cd "$(dirname "$0")/../../.." || exit 1
SRC=tools/omr/offroster_name.py
BAK=$(mktemp)
cp "$SRC" "$BAK"
restore() { cp "$BAK" "$SRC"; }
trap restore EXIT

summary() {  # the pytest tally line, never a stray DeprecationWarning
  python3 -m pytest tools/omr/tests/test_offroster_name.py -q -p no:warnings \
      2>&1 | grep -E "passed|failed|error" | tail -1
}
run() {  # run <label>
  echo "  break: $1"
  echo "    -> $(summary)"
}

echo "=== baseline (must be all green)"
summary

echo "=== 1. the veto never fires (rule removed)"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("        if name in admissible:\n            continue\n",
              "        if True:\n            continue\n")
p.write_text(s)
PY
run "if name in admissible -> if True"

echo "=== 2. an empty roster STRIPS instead of abstaining (the dangerous one)"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("    if not admissible:\n        return []\n",
              "    if admissible is None:\n        admissible = set()\n")
p.write_text(s)
PY
run "the abstention guard removed"

echo "=== 3. a READ name becomes vetoable (source scope widened)"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace('VETOABLE_SOURCES = ("score_order",)',
              'VETOABLE_SOURCES = ("score_order", "score_order_ambiguity", '
              '"label")')
p.write_text(s)
PY
run "VETOABLE_SOURCES widened to include label + ambiguity"

echo "=== 4. the speaks-for-itself exemption REINSTATED (the measured reversal)"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("        if name in admissible:\n            continue\n",
              "        if name in admissible:\n            continue\n"
              "        if ev.get(page_index, {}).get(staff_index) is not None:"
              "\n            continue\n")
p.write_text(s)
PY
run "exemption put back — this is what leaves 4 of 17 standing"

echo "=== 5. the flag defaults ON"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace('DEFAULT_MODE = "off"', 'DEFAULT_MODE = "on"')
p.write_text(s)
PY
run "DEFAULT_MODE off -> on"

echo "=== 6. the summary cannot tell abstention from a clean run"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace('"roster": sorted(admissible) if admissible else None,',
              '"roster": sorted(admissible or []),')
p.write_text(s)
PY
run "roster: None collapsed to []"

echo "=== 7. WIRING: the veto's keys never reach vetoed_keys"
restore
CBAK=$(mktemp); cp tools/omr/contextual.py "$CBAK"
python3 - tools/omr/contextual.py <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("vetoed_keys = vetoed_keys | offroster_vetoed_keys",
              "vetoed_keys = vetoed_keys  # offroster_vetoed_keys dropped")
p.write_text(s)
PY
run "union removed"
cp "$CBAK" tools/omr/contextual.py

echo "=== 8. WIRING: the two vetoes share one marker"
python3 - tools/omr/contextual.py <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace('                    staff["instrument_veto"] = (\n'
              '                        "offroster_name" if key in '
              'offroster_vetoed_keys\n'
              '                        else "absent_instrument")',
              '                    staff["instrument_veto"] = '
              '"absent_instrument"')
p.write_text(s)
PY
run "markers merged"
cp "$CBAK" tools/omr/contextual.py

echo "=== 9. the module grows a catalog reader of its own"
restore
python3 - "$SRC" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text()
s = s.replace("VETOABLE_SOURCES = (\"score_order\",)",
              "import json\nCATALOG = 'data/score-library/catalog.json'\n"
              "VETOABLE_SOURCES = (\"score_order\",)")
p.write_text(s)
PY
run "json import + catalog.json path added to the module body"

restore
echo "=== restored; baseline again"
summary
