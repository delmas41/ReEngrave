#!/usr/bin/env bash
# l281_run_all: regenerate everything ROADMAP 2.81 Phase 1 measured (FINDINGS.md section 17).
# MACHINE-LOCAL: it needs the shared overnight records (`library/_shared-records/*-20261010-night*`),
# the Brahms / Litolff edition PDFs, the symlinked weights + venvs (CLAUDE.md 5a) and about 2 GB of
# scratch. The two overnight records are streamed with `ijson` (record_io.load_record needs ~6.6x the file
# resident); the small quick record is also loaded the sanctioned way, by `l281_control.py`, to check the
# stream reader against it.
#
#   SCRATCH=/some/dir probe/l281_run_all.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
SCRATCH="${SCRATCH:-/tmp/l281}"
OUT="$HERE/out/l281"
mkdir -p "$SCRATCH/ext" "$SCRATCH/quick" "$OUT"
cd "$REPO"
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python OMR_SURYA_KEEP_ALIVE=0

# 1. the small re-gather (pages 0-1, GATHER+ADJUDICATE only; minutes) -> the quick record
if [ ! -f "$SCRATCH/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json" ]; then
  python3 -m tools.omr.acceptance_quick --doc brahms1-breitkopf --out-root "$SCRATCH/quick"
fi
Q="$SCRATCH/quick/out/brahms1-breitkopf/brahms1-breitkopf-p1.record.json"

# 2. stream the three records (each pass is ~30 s on Brahms)
for pair in "brahms:$LIB/brahms1-breitkopf-mvt1-whole-20261010-night.record.json" \
            "litolff:$LIB/beethoven5-litolff-mvt1-whole-20261010-night.record.json" \
            "bquick:$Q"; do
  tag="${pair%%:*}"; rec="${pair#*:}"
  for w in obs abs ver prov; do
    python3 "$HERE/l281_extract.py" --what "$w" --record "$rec" --out "$SCRATCH/ext/$tag-$w.json" > /dev/null
  done
done

# 3. the control: the stream reader against the sanctioned reader, head by head, on the small record
python3 "$HERE/l281_control.py" --record "$Q" --ext "$SCRATCH/ext" --tag bquick > "$OUT/control.txt"

# 4. the population, per record
for tag in brahms litolff bquick; do
  python3 "$HERE/l281_population.py" --tag "$tag" --ext "$SCRATCH/ext" --json "$SCRATCH/ext/$tag-pop.json" \
    --csv "$OUT/population-$tag.csv" > "$OUT/population-$tag.txt"
done

# 5. hand truth: the truth derivation, the scored page-0 members (quick record = current tree; the
#    overnight record = what the later stages did), what the later stages did, the wrong cases, the tip probe
python3 "$HERE/l281_truth.py" > "$OUT/truth-derivation.txt"
python3 "$HERE/l281_score.py" --tag bquick --ext "$SCRATCH/ext" --json "$SCRATCH/ext/bquick-p0-scored.json" > "$OUT/hand-truth-score-quick.txt"
python3 "$HERE/l281_score.py" --tag brahms --ext "$SCRATCH/ext" --json "$SCRATCH/ext/brahms-p0-scored.json" > "$OUT/hand-truth-score-overnight.txt"
python3 "$HERE/l281_wrong.py" --ext "$SCRATCH/ext" --tag bquick --scored "$SCRATCH/ext/bquick-p0-scored.json" > "$OUT/hand-truth-wrong-and-strokes.txt"
python3 "$HERE/l281_later.py" --ext "$SCRATCH/ext" --tag brahms --scored "$SCRATCH/ext/brahms-p0-scored.json" > "$OUT/later-stages-brahms.txt"
python3 "$HERE/l281_later.py" --ext "$SCRATCH/ext" --tag litolff > "$OUT/later-stages-litolff.txt"
python3 "$HERE/l281_tipprobe.py" --scored "$SCRATCH/ext/bquick-p0-scored.json" --cache "$SCRATCH/p0_rgb.npy" > "$OUT/tip-ink-probe.txt"

# 5b. the print crops of the hand-truth page: the 22 heads his boxes say are beamed/flagged, the 54 they say
#     are bare (CLEAN crops, a bracket on the head and nothing else of ours), and the one head the print check
#     reclassified (a flag on the print his page does not box)
CK="$REPO/out/print/2.81-hand-truth-check"
mkdir -p "$CK"
python3 "$HERE/l281_sheet.py" --scored "$SCRATCH/ext/bquick-p0-scored.json" --out-dir "$CK/wrong_cases" \
  --cache "$SCRATCH/p0_rgb.npy" --judge wrong_beam --per 12 --cols 4 --scale 0.8 > /dev/null
python3 "$HERE/l281_sheet.py" --scored "$SCRATCH/ext/bquick-p0-scored.json" --out-dir "$CK/bare_heads" \
  --cache "$SCRATCH/p0_rgb.npy" --judge right --per 15 --cols 5 --scale 0.7 > /dev/null
python3 "$HERE/l281_view.py" --rect 2850,4960,3250,5260 --pad 10 --scale 1.5 --bracket 2998.66,4998.35,3040.59,5038.34 \
  --cache "$SCRATCH/p0_rgb.npy" --out "$CK/g0_0_9_2_2_flag_unboxed_with_truth_boxes.png" > /dev/null
python3 "$HERE/l281_view.py" --rect 2850,4960,3250,5260 --pad 10 --scale 1.5 --no-boxes --bracket 2998.66,4998.35,3040.59,5038.34 \
  --cache "$SCRATCH/p0_rgb.npy" --out "$CK/g0_0_9_2_2_flag_unboxed_clean.png" > /dev/null

# 6. the blind tiles (fixed seed 20261010) -> out/print/2.81-review/
python3 "$HERE/l281_tiles.py" --ext "$SCRATCH/ext" --out "$REPO/out/print/2.81-review" \
  --scored "$SCRATCH/ext/bquick-p0-scored.json" --controls 4
python3 "$HERE/l281_manifest.py" --dir "$REPO/out/print/2.81-review" > "$OUT/tiles-our-reading.txt"
echo "done: $OUT"
