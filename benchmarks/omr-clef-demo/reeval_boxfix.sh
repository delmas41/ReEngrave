#!/bin/bash
# Re-validate the corrected (box-fix) clef retrain: clef accuracy + non-clef
# forgetting. Run from repo root AFTER training completes. CPU evals.
set -e
cd /Users/seanjohnson/Desktop/ReEngrave

RUN=runs/detect/omr-weights/clef-ft-runs/clef-ft-boxfix
NEW=omr-weights/deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt
PROD=omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
OLD_FT=omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt
OUT=benchmarks/omr-clef-demo

echo "=== copying last.pt -> $NEW ==="
cp "$RUN/weights/last.pt" "$NEW"
ls -la "$NEW"

echo; echo "=== CLEF eval: 44-cell baseline set ==="
python3 -m tools.omr.training.clef_count_eval --weights "$NEW" \
  --cells-dir benchmarks/omr-labeling-2026-07-12-clef/cells \
  --verdicts-dir benchmarks/omr-labeling-2026-07-12-clef/verdicts \
  --imgsz 1280 --conf 0.20 | tee "$OUT/clef_eval_boxfix_44cell.txt"

echo; echo "=== CLEF eval: clef-diverse set ==="
python3 -m tools.omr.training.clef_count_eval --weights "$NEW" \
  --cells-dir benchmarks/omr-labeling-clef-diverse/cells \
  --verdicts-dir benchmarks/omr-labeling-clef-diverse/verdicts \
  --imgsz 1280 --conf 0.20 | tee "$OUT/clef_eval_boxfix_diverse.txt"

echo; echo "=== WTC forgetting audit: production vs box-fix (center) ==="
python3 -m tools.omr.training.wtc_forgetting_eval --prod "$PROD" --ft "$NEW" \
  --cells-dir benchmarks/omr-phase2.5/cells \
  --detections-dir benchmarks/omr-phase3.4/detections-yolo-realft \
  --verdicts-dir benchmarks/omr-phase3.4/verdicts-yolo-realft-ported \
  --prefix wtc --imgsz 1280 --conf 0.25 --match center \
  --json-out "$OUT/wtc_forgetting_boxfix_center.json" | tee "$OUT/wtc_forgetting_boxfix_center.txt"

echo "REEVAL DONE"
