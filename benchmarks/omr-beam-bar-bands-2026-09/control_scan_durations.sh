#!/usr/bin/env bash
# Which DURATIONS actually change on the scans — through the real pipeline.
#
# `probe_bar_placement.py` counts a level change for every detected stem, which
# is an UPPER BOUND: `rhythm` only calls `_beams_attached_to_stem` for a stem
# that `_stem_for_notehead` matched to a notehead, and only a matched stem's
# level reaches a note's duration. A spurious stem can change its count without
# changing anything that is exported.
#
# So this runs `transcribe` + `export` under both placements and diffs the
# MusicXML. That is the ground truth for the acceptance question and it is not
# a proxy for it.
#
#   bash benchmarks/omr-beam-bar-bands-2026-09/control_scan_durations.sh ROW_ID [ROW_ID...]
#
# ⚠️ Direction text and the contextual pass are OFF on both arms: neither
# touches beams, both are nondeterministic run to run, and a controlled A/B
# must differ only in the thing under test.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LIB="${OMR_LIBRARY_ROOT:-/Users/seanjohnson/Desktop/ReEngrave/library}"
OUT="${OUT_DIR:-/tmp/beam-band-scans}"
SRC="$REPO/tools/omr/line_detection.py"
ROWS="$REPO/benchmarks/omr-scan-e2e-2026-09/works.json"

[ $# -ge 1 ] || { echo "FATAL: name at least one row_id" >&2; exit 2; }
mkdir -p "$OUT"
cp "$SRC" "$OUT/line_detection.orig.py"
restore() { cp "$OUT/line_detection.orig.py" "$SRC"; }
trap restore EXIT
cd "$REPO"

run_arm () {                                   # $1 = arm name
  for row in "${ROWS_WANTED[@]}"; do
    read -r pdf page < <(python3 - "$ROWS" "$row" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))["rows"]
for r in rows:
    if r["row_id"] == sys.argv[2]:
        print(r["edition"]["catalog_path"], r["page"]["pdf_page_index"]); break
else:
    sys.exit("FATAL: unknown row_id " + sys.argv[2])
PY
)
    [ -f "$LIB/$pdf" ] || { echo "FATAL: missing $LIB/$pdf" >&2; exit 2; }
    echo "  [$1] $row (page $page)"
    OMR_DIRECTION_TEXT=0 OMP_NUM_THREADS=2 python3 -u -m tools.omr.transcribe \
      "$LIB/$pdf" --pages "$page" --no-contextual \
      --out "$OUT/$row.$1.json" >"$OUT/$row.$1.stderr" 2>&1 \
      || { echo "FATAL: transcribe failed for $row ($1); see $OUT/$row.$1.stderr" >&2; exit 2; }
    python3 -m tools.omr.export "$OUT/$row.$1.json" --format musicxml \
      --out "$OUT/$row.$1.musicxml" >/dev/null
  done
}

ROWS_WANTED=("$@")

echo "=== ARM B: emission site reverted to the even division ==="
python3 - "$SRC" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); s = p.read_text()
old = """        if bands is None:
            sub_h = max(1, h // n_bars)
            placed = [(int(y + k * (h / n_bars)), int(sub_h))
                      for k in range(n_bars)]
        else:
            placed = [(int(y + top), max(1, int(bottom - top + 1)))
                      for top, bottom in bands]"""
new = """        sub_h = max(1, h // n_bars)
        placed = [(int(y + k * (h / n_bars)), int(sub_h)) for k in range(n_bars)]"""
assert old in s, "FATAL: emission site not found — the control would be vacuous"
p.write_text(s.replace(old, new))
PY
run_arm even
restore
trap - EXIT

echo "=== ARM A: with the fix (measured bands) ==="
run_arm fixed

echo
python3 "$REPO/benchmarks/omr-beam-bar-bands-2026-09/diff_durations.py" \
        --out-dir "$OUT" --rows "${ROWS_WANTED[@]}"
