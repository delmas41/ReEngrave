#!/bin/bash
# 3-way eval (runs on the Mac after downloading the two best.pt).
# Baseline = production, Arm A = fine-tune-on-augmented, Arm B = fine-tune-on-clean.
#   1) DENSE recall on 140 hand-labeled real orchestral cells (beet5/mahler5/lamer)
#   2) WTC regression (must not drop keyboard-Bach recall vs Baseline)
# Run from the worktree root:  bash benchmarks/scoreaug-fair-test/run_eval.sh
set -e
WT=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/scoreaug-fair-test-a2928e
MAIN=/Users/seanjohnson/Desktop/ReEngrave
W=$MAIN/omr-weights
FT=$W/scoreaug-fair-test
OUT=$WT/benchmarks/scoreaug-fair-test
cd "$WT"
PROD=$W/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
A=$FT/ft-scoreaug-armA-best.pt
B=$FT/ft-clean-armB-best.pt
for f in "$PROD" "$A" "$B"; do [ -f "$f" ] || { echo "MISSING $f"; exit 1; }; done

echo "############ DENSE notehead recall  (imgsz 1280, conf 0.25) ############"
PYTHONPATH=. python3 -m tools.omr.training.eval_dense_recall \
    --weights "$PROD" "$A" "$B" --labels production armA armB \
    --repo-root "$MAIN" --imgsz 1280 --conf 0.25 --device cpu \
    --json-out "$OUT/dense_recall_1280_c25.json"

echo "############ DENSE recall spray-check  (imgsz 1280, conf 0.50) ############"
PYTHONPATH=. python3 -m tools.omr.training.eval_dense_recall \
    --weights "$PROD" "$A" "$B" --labels production armA armB \
    --repo-root "$MAIN" --imgsz 1280 --conf 0.50 --device cpu \
    --json-out "$OUT/dense_recall_1280_c50.json"

echo "############ WTC regression  (prod vs each arm, prefix wtc, center) ############"
for pair in armA:ft-scoreaug-armA armB:ft-clean-armB; do
  tag=${pair%%:*}; run=${pair##*:}
  echo "---- $tag ----"
  PYTHONPATH=. python3 -m tools.omr.training.wtc_forgetting_eval \
    --prod "$PROD" --ft "$FT/$run-best.pt" \
    --cells-dir "$MAIN/benchmarks/omr-phase2.5/cells" \
    --detections-dir benchmarks/omr-phase3.4/detections-yolo-realft \
    --verdicts-dir   benchmarks/omr-phase3.4/verdicts-yolo-realft-ported \
    --prefix wtc --imgsz 1280 --conf 0.25 --match center --device cpu \
    --json-out "$OUT/wtc_${tag}.json"
done
echo "ALL_EVAL_DONE -> $OUT"
