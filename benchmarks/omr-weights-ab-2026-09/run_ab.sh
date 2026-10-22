#!/usr/bin/env bash
# Sean's A/B: graft candidate weights into a COPY of production and compare
# the two on the output of GATHER + ADJUDICATE alone (ROADMAP 2.34 / 2026-
# 09-29 DECISIONS: "take newly grafted weights and add them to a copy of
# production and compare the 2 ... at the output of the first two stages").
#
# `--through adjudicate` (ROADMAP 2.34, same landing) makes that literal:
# no GROUPS/EVALUATE/INFER, so nothing downstream of ADJUDICATE can make
# the two arms agree or disagree for a reason that has nothing to do with
# the weights.
#
# Usage:
#   ./run_ab.sh <pdf> <pages> <label_a>=<weights_a> <label_b>=<weights_b> \
#       [<pdf_basename_for_cross_reference>]
#
# Example (the one-page proof this benchmark ships with):
#   ./run_ab.sh \
#       "$MAIN/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf" \
#       1 \
#       production=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt \
#       candidate=omr-weights/candidates/rest-exp-E-epoch0-graft-2026-09-29.pt \
#       brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PDF="${1:?usage: run_ab.sh <pdf> <pages> <label>=<weights> <label>=<weights> [pdf_basename]}"
PAGES="${2:?pages}"
ARM_A="${3:?label_a=weights_a}"
ARM_B="${4:?label_b=weights_b}"
PDF_BASENAME="${5:-}"

LABEL_A="${ARM_A%%=*}"; WEIGHTS_A="${ARM_A#*=}"
LABEL_B="${ARM_B%%=*}"; WEIGHTS_B="${ARM_B#*=}"

OUT_DIR="benchmarks/omr-weights-ab-2026-09/out/${LABEL_A}-vs-${LABEL_B}"
mkdir -p "$OUT_DIR"

echo "=== gathering+adjudicating with $LABEL_A ($WEIGHTS_A) ==="
python3 -m tools.omr.staged "$PDF" --pages "$PAGES" --weights "$WEIGHTS_A" \
    --through adjudicate --no-surya --no-ocr \
    --out "$OUT_DIR/rec-${LABEL_A}.json"

echo "=== gathering+adjudicating with $LABEL_B ($WEIGHTS_B) ==="
python3 -m tools.omr.staged "$PDF" --pages "$PAGES" --weights "$WEIGHTS_B" \
    --through adjudicate --no-surya --no-ocr \
    --out "$OUT_DIR/rec-${LABEL_B}.json"

echo "=== diffing the two records ==="
XREF_ARGS=()
if [ -n "$PDF_BASENAME" ]; then
  XREF_ARGS=(--pdf-name "$PDF_BASENAME" \
             --verdicts-dir benchmarks/omr-queue-rests-2026-09/verdicts \
             --cells-json benchmarks/omr-queue-rests-2026-09/cells.json)
fi

python3 benchmarks/omr-weights-ab-2026-09/diff_records.py \
    --a "$OUT_DIR/rec-${LABEL_A}.json" --b "$OUT_DIR/rec-${LABEL_B}.json" \
    --label-a "$LABEL_A" --label-b "$LABEL_B" \
    --family rest --pages "$PAGES" \
    --out-json "$OUT_DIR/summary.json" --out-md "$OUT_DIR/TABLE.md" \
    "${XREF_ARGS[@]}"

echo "=== $OUT_DIR/TABLE.md ==="
cat "$OUT_DIR/TABLE.md"
