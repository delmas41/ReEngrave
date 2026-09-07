#!/usr/bin/env bash
# The byte-identity control: engraved fixtures must export IDENTICAL MusicXML.
#
# 0 of 258 components on the eleven engraved pages read more than one bar, so
# this is guaranteed by construction — which is exactly what makes it the
# cleanest control available. It proves the wiring rather than the arithmetic:
# a mistake in the single-bar fall-through would show up here even though the
# multi-bar path is never entered.
#
# Runs both arms in ONE tree by patching the emission site between them, so the
# only difference between the arms is the placement expression itself.
#
#   bash benchmarks/omr-beam-bar-bands-2026-09/control_export_identity.sh brahms-sym1-mvt1 mozart-sym41-mvt1
#
# ⚠️ Direction text and the contextual pass are OFF on both arms. Neither
# touches beams, and both are nondeterministic across runs (Surya temperature,
# detector jitter) — leaving them on would produce diffs that are not this
# change and mask ones that are.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIXTURES="${OMR_FIXTURE_ROOT:-/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/fixtures}"
OUT="${OUT_DIR:-/tmp/beam-band-control}"
SRC="$REPO/tools/omr/line_detection.py"

[ $# -ge 1 ] || { echo "FATAL: name at least one fixture" >&2; exit 2; }
mkdir -p "$OUT"
cp "$SRC" "$OUT/line_detection.orig.py"
restore() { cp "$OUT/line_detection.orig.py" "$SRC"; }
trap restore EXIT

run_arm () {                      # $1 = arm name
  for work in "${WORKS[@]}"; do
    pdf="$FIXTURES/$work.pdf"
    [ -f "$pdf" ] || { echo "FATAL: missing fixture $pdf" >&2; exit 2; }
    OMR_DIRECTION_TEXT=0 OMP_NUM_THREADS=2 python3 -u -m tools.omr.transcribe \
      "$pdf" --pages 0 --no-contextual --out "$OUT/$work.$1.json" >/dev/null
    python3 -m tools.omr.export "$OUT/$work.$1.json" \
      --format musicxml --out "$OUT/$work.$1.musicxml" >/dev/null
  done
}

WORKS=("$@")
cd "$REPO"

echo "=== ARM A: with the fix (measured bands) ==="
run_arm fixed

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
print("  patched to the pre-fix placement")
PY
run_arm even
restore
trap - EXIT

echo
fail=0
for work in "${WORKS[@]}"; do
  if cmp -s "$OUT/$work.fixed.musicxml" "$OUT/$work.even.musicxml"; then
    echo "  IDENTICAL  $work"
  else
    echo "  DIFFERS    $work"
    diff <(sed 's/></>\n</g' "$OUT/$work.even.musicxml") \
         <(sed 's/></>\n</g' "$OUT/$work.fixed.musicxml") | head -40
    fail=1
  fi
done
[ "$fail" -eq 0 ] && echo "CONTROL PASSED: every engraved export byte-identical" \
                  || { echo "CONTROL FAILED"; exit 1; }
