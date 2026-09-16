#!/usr/bin/env bash
#
# PRICE THE FLIP END TO END, on the document whose meter reading is KNOWN BAD.
#
#   bash benchmarks/omr-meter-corroboration-2026-09/local_arm.sh \
#       <path to the Breitkopf Brahms 1 PDF> \
#       [weights] [pages]
#
# Example (paths as CLAUDE.md records them on Sean's machine):
#
#   bash benchmarks/omr-meter-corroboration-2026-09/local_arm.sh \
#     library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
#     omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
#     0-3
#
# ⚠️⚠️ **THIS ARM CANNOT RUN IN A CLOUD CONTAINER AND WAS NEVER RUN.** There is
# no `omr-weights/` and no `library/` there, so nothing below has been
# executed; it is written from the boundary session's own `run_arms.py`, which
# HAS run this document. Treat every number it prints as new.
#
# WHY THIS DOCUMENT. `OMR_METER_CARRY` was held off on **n**, and the standing
# blocking objection is that on a scan whose meter GLYPHS are misread the
# weighing never gets a fair candidate: Breitkopf Brahms 1 votes `9/4` for a
# printed `9/8`, misses the real change, and proposes spurious `4/4` changes
# just over the floor. Its engraved twin is 4-for-4 on the same 22 bars. So
# this is the document where the flip's COST shows if it shows anywhere, and
# `probe/bar_fill.py` — *"only 38.0% of exported bars sum to the `<time>` the
# same file declares"* — is where it shows.
#
# ⚠️ A-METER-6 does NOT fix the misread `9/4` OPENING and this arm will not
# show it fixed. The guard stops a ONE-STAFF CHANGE spreading across pages;
# where the majority is wrong it is silent, by construction.
#
# WHAT IT DOES
#   ARM A  both flags OFF  — the pre-2026-09-15 default
#   ARM B  both flags ON   — the shipped default, with A-METER-6
#   then, for each arm: export, count `<time>` elements, and run the bar-fill
#   probe, which is the instrument Sean's *"none of the measure math makes
#   sense"* observation was turned into.
#
# ⚠️ EVERY ARM GETS ITS OWN `--out`, BOTH VARIABLES ARE SET EXPLICITLY IN EVERY
# ARM, AND THE ENVIRONMENT IS PASSED PER COMMAND rather than through an
# unquoted expansion — the three traps `run_arms.py` documents (a cached A/B
# reports "identical" whatever the change did; zsh does not word-split
# `env $VARS python3 ...`, so a two-variable arm silently sets one).
#
# ⚠️ LAND EVERY EDIT BEFORE STARTING. `staged/__main__.py` imports the exporter
# AFTER the gather and an already-imported module keeps the code it was loaded
# with, so an edit made mid-run reaches one half and not the other.
set -euo pipefail

PDF="${1:?usage: local_arm.sh <pdf> [weights] [pages] [bar-beats]}"
WEIGHTS="${2:-omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt}"
PAGES="${3:-0-3}"
# ⚠️ THE DOCUMENT'S BAR LENGTH IN QUARTER NOTES, and it has no safe default.
# Brahms 1 mvt 1 is 6/8 = 3.0; Litolff Beethoven 5 mvt 1 is 2/4 = 2.0. The
# 2026-09-16 run took `bar_fill.py`'s old default of 2.0 on the Brahms and
# reported 96.3% OVERFULL, counting every correctly-sized 3.0 bar as too long.
BAR_BEATS="${4:?bar-beats is REQUIRED: the bar length in quarter notes for THIS document -- 6/8=3.0, 2/4=2.0, 4/4=4.0. There is no safe default; see the comment above.}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="$HERE/out/local"
mkdir -p "$OUT"
cd "$ROOT"

echo "=============================================================="
echo "A-METER-6 + the default flip, priced end to end"
echo "  pdf     : $PDF"
echo "  weights : $WEIGHTS"
echo "  pages   : $PAGES"
echo "  tree    : $(git rev-parse --short HEAD)$(git status --porcelain | grep -q . && echo ' (DIRTY -- the arms cannot be attributed)')"
echo "=============================================================="

for ARM in OFF ON; do
  if [ "$ARM" = "OFF" ]; then CARRY=0; BARS=0; else CARRY=1; BARS=1; fi
  REC="$OUT/brahms1-$ARM.json"
  XML="$OUT/brahms1-$ARM.musicxml"
  if [ -f "$REC" ]; then
    echo ""
    echo "!! $REC exists. A cached arm reports 'identical' whatever the change"
    echo "!! did, and nothing about the output invites suspicion. Delete it or"
    echo "!! use a fresh out dir."
    exit 2
  fi
  echo ""
  echo "--- ARM $ARM  (OMR_METER_CARRY=$CARRY OMR_METER_FROM_BARS=$BARS) ---"
  # ⚠️ NO `--musicxml`: the exporter is imported AFTER the gather, so a long
  # gather picks up whatever `export.py` says when it finally reaches EXPORT.
  # Export separately, below.
  OMR_METER_CARRY=$CARRY OMR_METER_FROM_BARS=$BARS OMR_SURYA_KEEP_ALIVE=0 \
    python3 -u -m tools.omr.staged "$PDF" --pages "$PAGES" \
      --weights "$WEIGHTS" --out "$REC"
  OMR_METER_CARRY=$CARRY OMR_METER_FROM_BARS=$BARS \
    python3 -m tools.omr.staged.export "$REC" --out "$XML"
done

echo ""
echo "=============================================================="
echo "BEFORE / AFTER"
echo "=============================================================="
python3 - "$OUT/brahms1-OFF.json" "$OUT/brahms1-ON.json" \
         "$OUT/brahms1-OFF.musicxml" "$OUT/brahms1-ON.musicxml" <<'PY'
import json, sys, collections, re

off_rec, on_rec, off_xml, on_xml = sys.argv[1:5]

def meters(path):
    """Every `meter` verdict of a run.

    ⚠️ A FULL RECORD nests them under `["record"]["verdicts"]` while the
    committed REDUCTIONS are a bare list — `report_boundary.meters` makes the
    same distinction and records that the reduction "could not be read back"
    when it did not. Both shapes are accepted here so this block can be
    pointed at either.
    """
    data = json.load(open(path))
    rows = (data["record"]["verdicts"] if isinstance(data, dict)
            else data)
    return [v for v in rows if v.get("quantity") == "meter"]

def summarise(path, label):
    rows = meters(path)
    by_reason = collections.Counter(r.get("reason") for r in rows)
    segs = uncorrob = 0
    for r in rows:
        value = r.get("value") or {}
        s = value.get("segments") or []
        s = s if r.get("reason") == "change_only" else s[1:]
        segs += len(s)
        uncorrob += sum(1 for x in s if x.get("corroborated") is False)
    skipped = sum(len((r.get("detail") or {}).get("skipped_uncorroborated") or [])
                  for r in rows)
    print(f"{label:6s} systems={len(rows):3d}  decided="
          f"{sum(1 for r in rows if r.get('outcome') == 'decided'):3d}"
          f"  change segments={segs:3d}  uncorroborated={uncorrob:3d}"
          f"  carry sources SKIPPED={skipped:3d}")
    print(f"         reasons: {dict(by_reason)}")
    return rows

print("-- the METER decisions --")
summarise(off_rec, "OFF")
summarise(on_rec, "ON")

print()
print("-- `<time>` elements in the file --")
for label, path in (("OFF", off_xml), ("ON", on_xml)):
    xml = open(path, encoding="utf-8").read()
    times = re.findall(r"<beats>(\d+)</beats>\s*<beat-type>(\d+)</beat-type>", xml)
    print(f"{label:6s} <time> total={len(times):4d}   "
          f"{dict(collections.Counter('%s/%s' % t for t in times))}")

print()
print("⚠️ A meter change this page does NOT print, exported on every staff, is")
print("   what the standing objection predicts. Compare the `9/4` and the")
print("   spurious `4/4` counts against the printed 6/8 + one bar of 9/8.")
PY

echo ""
echo "=============================================================="
echo "BAR FILL -- the instrument Sean's observation 5 became"
echo "=============================================================="
for ARM in OFF ON; do
  echo "--- $ARM ---"
  # ⚠️ `--bar-beats` IS NOW REQUIRED AND THIS ARM USED TO OMIT IT, taking the
  # probe's old default of 2.0 — Litolff Beethoven 5's 2/4 — on a Brahms 6/8
  # document. The 2026-09-16 run reported 96.3% OVERFULL / 0.6% exact and the
  # whole figure was that constant. 6/8 is 3.0 quarter notes.
  python3 benchmarks/omr-rest-sizing-2026-09/probe/bar_fill.py \
    --bar-beats "$BAR_BEATS" \
    "$OUT/brahms1-$ARM.musicxml" || true
done

cat <<'NOTE'

==============================================================
HOW TO READ IT
==============================================================
* `bars that add up` RISING is the flip working: a system with no meter pads
  its empty bars at a default 4.0 quarters, and a carried meter sizes them.
  On Litolff Beethoven 5 pp.1-4 the same arm measured 38.0% -> 69.2%.
* `<time>` elements RISING FAST is the standing objection arriving: a scan can
  now export a meter change its page does not print. `OMR_METER_SEGMENTS`'
  own row records 41 -> 138 on this document for the SEGMENTS flag alone.
* `carry sources SKIPPED` is A-METER-6's reach on a real gather — the number
  no committed record can supply, and the one thing this arm exists to get.
* ⚠️ If `bars that add up` FALLS, the flip is propagating the misread `9/4`
  and that is the cost side the flag was held off for. Report it; do not tune
  METER_CARRY_FLOOR against it (this project has refused that twice).
NOTE
