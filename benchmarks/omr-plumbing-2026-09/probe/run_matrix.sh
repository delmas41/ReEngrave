#!/bin/bash
# The overnight plumbing matrix: every fixture x every flag flip.
#
# ⚠️ PLUMBING, NOT QUALITY. Nothing here scores a reading. Each run asks only
# whether the stages completed and which declared connections carried a value.
#
# ⚠️ COMMIT BEFORE RUNNING. `staged/__main__.py` stamps provenance (commit +
# dirty) on every record, and editing ANY file -- including an untracked one
# under benchmarks/ -- makes `provenance.dirty` true, which makes every record
# this matrix writes unattributable.
set -u
cd "$(dirname "$0")/../../.." || exit 2
ROOT=$PWD
FIX=benchmarks/omr-plumbing-2026-09/fixture
OUT=${OUT:-benchmarks/omr-plumbing-2026-09/out/matrix}
W=/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
mkdir -p "$OUT"
LOG=$OUT/run.log
: > "$LOG"

say(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }
say "tree $(git rev-parse --short HEAD) dirty=$(test -n "$(git status --porcelain)" && echo yes || echo no)"

FIXTURES="plumbing v2_marks v3_lineup v4_changes v5_dense v6_scanlike"
OFF_FLAGS="OMR_ARC_RECLASS OMR_CONTEST_DUMP OMR_CV_HAIRPINS OMR_DIRECTION_TEXT_SCAN_GATE OMR_INSTRUMENT_CLEF_DEFAULT OMR_LINEUP_SWAP_SPLIT OMR_METER_TEMPLATE_AT_BAR OMR_ROSTER_CLEF OMR_ROSTER_LABELS OMR_SCORE_LANGUAGE"
ON_FLAGS="OMR_BRACKET_COLUMNS OMR_CHOIR_GROUPING OMR_DIRECTION_TEXT OMR_LABEL_MERGE_QUALITY OMR_LEFT_EDGE_SPLIT OMR_METER_CARRY OMR_METER_FROM_BARS OMR_METER_SEGMENTS OMR_MOVEMENT_REFERENCE OMR_ROSTER OMR_SLOT_STITCH OMR_WHOLE_REST_INK"

run(){  # run <tag> <fixture> <extra-env...>
  local tag=$1 fx=$2; shift 2
  local rec=$OUT/$tag.record.json
  [ -f "$rec" ] && { say "skip $tag (exists)"; return 0; }
  local t0=$SECONDS
  env OMR_INFER=1 "$@" python3 -m tools.omr.staged "$FIX/$fx.pdf" \
      --pages 0 --weights "$W" --no-surya --no-ocr \
      --out "$rec" --musicxml "$OUT/$tag.musicxml" \
      > "$OUT/$tag.stdout" 2> "$OUT/$tag.stderr"
  local rc=$? dt=$((SECONDS-t0))
  say "$(printf '%-44s' "$tag") rc=$rc ${dt}s"
  [ $rc -ne 0 ] && tail -4 "$OUT/$tag.stderr" >> "$LOG"
  return 0
}

say "=== 1. base arm, every fixture ==="
for fx in $FIXTURES; do run "base__$fx" "$fx"; done

say "=== 2. determinism: the base fixture twice ==="
run "determinism__plumbing" plumbing

say "=== 3. every default-OFF flag, turned ON, on every fixture ==="
for f in $OFF_FLAGS; do for fx in $FIXTURES; do run "on_${f}__$fx" "$fx" "$f=1"; done; done

say "=== 4. every default-ON flag, turned OFF, on every fixture ==="
for f in $ON_FLAGS; do for fx in $FIXTURES; do run "off_${f}__$fx" "$fx" "$f=0"; done; done

say "=== 5. the OCR rungs (margin labels + direction words) ==="
for fx in plumbing v3_lineup v6_scanlike; do
  tag="ocr__$fx"; rec=$OUT/$tag.record.json
  if [ ! -f "$rec" ]; then
    t0=$SECONDS
    env OMR_INFER=1 python3 -m tools.omr.staged "$FIX/$fx.pdf" --pages 0 --weights "$W" \
        --out "$rec" --musicxml "$OUT/$tag.musicxml" > "$OUT/$tag.stdout" 2> "$OUT/$tag.stderr"
    say "$(printf '%-44s' "$tag") rc=$? $((SECONDS-t0))s"
  fi
done

say "=== 6. NEGATIVE CONTROL: no weights at all ==="
tag=noweights__plumbing
if [ ! -f "$OUT/$tag.record.json" ]; then
  env OMR_INFER=1 python3 -m tools.omr.staged "$FIX/plumbing.pdf" --pages 0 --no-surya --no-ocr \
      --out "$OUT/$tag.record.json" --musicxml "$OUT/$tag.musicxml" \
      > "$OUT/$tag.stdout" 2> "$OUT/$tag.stderr"
  say "$(printf '%-44s' "$tag") rc=$?"
fi

say "=== 7. pooling every arm through the edge test ==="
python3 benchmarks/omr-plumbing-2026-09/probe/edges.py "$OUT"/*.record.json \
    --json "$OUT/edges.json" > "$OUT/EDGES.txt" 2>&1
say "edges exit=$? -> $OUT/EDGES.txt"
tail -20 "$OUT/EDGES.txt" | tee -a "$LOG"
say "DONE. records=$(ls "$OUT"/*.record.json 2>/dev/null | wc -l | tr -d ' ')"
