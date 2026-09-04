#!/usr/bin/env bash
# Compile a specialist ENSEMBLE into one set of weights, one family at a time.
#
# The literal "one YOLO per symbol, swept over the page" costs one forward pass
# per specialist — twenty of them turns a 2.5-minute page into fifty. But a
# YOLOv8 head is per-class in its last 1x1 conv, so a specialist's knowledge of
# its own symbol lives in that symbol's rows and nowhere else. Transplant those
# rows and you get the ensemble at the cost of ONE pass.
#
# Composition is just `merge_class_head.py` applied repeatedly: graft family 1
# into production, then family 2 into THAT, and so on. Each step keeps its own
# family's rows from its specialist and takes every other row from the running
# composite, so earlier grafts survive.
#
# ⚠️ **This is only sound if the specialists share the composite's FEATURES.**
# A row is a linear readout of whatever the neck hands it; transplant it onto
# different features and it reads something else — which is why round 5's graft
# left `ledgerLine` at 11 instead of the base's 57. Train the specialists with
# `freeze: 22` (everything but `model.22`) FROM the same checkpoint you compose
# onto, and the features are bit-identical by construction. The `freeze22` arm
# is what tests that; until it passes, treat a multi-family composite as
# unverified and gate each family on its own.
#
#   ./compose_specialists.sh <out.pt> <family>=<specialist.pt> [...]
#   BIAS_SHIFT=0.9 ./compose_specialists.sh ...
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$ROOT"
OUT="${1:?usage: compose_specialists.sh <out.pt> <family>=<ckpt.pt> ...}"; shift
MAIN=/Users/seanjohnson/Desktop/ReEngrave
PROD="${PROD:-$MAIN/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt}"
SHIFT="${BIAS_SHIFT:-0.9}"
MERGE=benchmarks/omr-labeling-survey-2026-09/merge_class_head.py

case_classes () {
  case "$1" in
    hollow) echo "noteheadHalfOnLine noteheadHalfInSpace noteheadWholeOnLine noteheadWholeInSpace noteheadHalfOnLineSmall noteheadHalfInSpaceSmall noteheadWhole" ;;
    ties)   echo "tie" ;;
    slurs)  echo "slur" ;;
    rests)  echo "restWhole restHalf restQuarter rest8th rest16th restHBar" ;;
    accidentals) echo "accidentalFlat accidentalNatural accidentalSharp" ;;
    clefs)  echo "clefG clefF clefC clefCAlto clefCTenor" ;;
    dots)   echo "augmentationDot" ;;
    dynamics) echo "dynamicP dynamicF dynamicM dynamicS dynamicCrescendoHairpin dynamicDiminuendoHairpin" ;;
    black)  echo "noteheadBlackOnLine noteheadBlackInSpace" ;;
    *) echo "unknown family: $1" >&2; exit 2 ;;
  esac
}

CUR="$PROD"
TMP="$(mktemp -d)"
i=0
for spec in "$@"; do
  fam="${spec%%=*}"; ckpt="${spec#*=}"
  i=$((i+1))
  next="$TMP/step${i}_${fam}.pt"
  echo "=== grafting $fam from $(basename "$ckpt") onto $(basename "$CUR")"
  python3 "$MERGE" --ft "$ckpt" --base "$CUR" --out "$next" \
      --labels-root data/user-labeled --bias-shift "$SHIFT" \
      --keep $(case_classes "$fam")
  CUR="$next"
done
mkdir -p "$(dirname "$OUT")"
cp "$CUR" "$OUT"
echo "composed $i specialist(s) at bias shift $SHIFT -> $OUT"
