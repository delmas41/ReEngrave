#!/usr/bin/env bash
# ROADMAP 2.4b step 2 -- the SHORT run: 1 epoch from PRODUCTION on the production recipe's mix, plus v24.
#   arms:  withv24  = v1-v4 (2x dense) + v13-v22 (teacher-completed, distill25 form) + v24
#          control  = the same without v24      (CONTROL=1: "1 epoch from production on the old mix" alone)
# imgsz 896 / 1 epoch / save_period 1 (the SHIP_RESULTS recipe; imgsz 2048 is infeasible on this machine).
# batch 8 not 16: ultralytics accumulates to a nominal batch of 64, so the optimizer-step count is identical;
# only the BatchNorm batch differs, and the box stays inside the memory the shared machine can spare.
# Machine discipline (two crashes this week): lock file the overnight re-gather waits on, removed by a trap.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT="$(pwd)"
LOCK=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/.training-2.4b.lock
NAME="${NAME:-hollow4-withv24}"
CONTROL="${CONTROL:-0}"
PROD=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
CLASSES=tools/omr/training/deepscoresv2_208_classes.json
CAT="runs/2.4b/cat-$NAME"
DENSE="v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer"
HOLLOW="v13-2026-09-03-complete-v7-beet5-bolero v14-2026-09-03-complete-litolff v15-2026-09-03-complete-peters v16-2026-09-03-complete-eulenburg v17-2026-09-03-complete-simrock v18-2026-09-03-complete-breitkopf v19-2026-09-03-complete-mahler1 v20-2026-09-03-complete-elgar1 v21-2026-09-03-complete-lamer v22-2026-09-04-simrock-dense"
V24=v24-2026-10-13-hollow4-train
VERSIONS="$DENSE $HOLLOW"; [ "$CONTROL" = 1 ] || VERSIONS="$VERSIONS $V24"
trap 'rm -f "$LOCK"' EXIT INT TERM
echo "2.4b $NAME pid $$ $(date -u +%FT%TZ)" > "$LOCK"
rm -rf "$CAT"; mkdir -p "$CAT"
for v in $DENSE $HOLLOW; do ln -sfn "$ROOT/data/user-labeled-distill25/$v" "$CAT/$v"; done
[ "$CONTROL" = 1 ] || ln -sfn "$ROOT/data/user-labeled/$V24" "$CAT/$V24"
python3 -m tools.omr.training.build_catalog_yaml --root "$CAT" --versions $VERSIONS --fallback-class-names "$CLASSES" >/dev/null
python3 benchmarks/omr-labeling-survey-2026-09/oversample_dense.py --catalog "$CAT/catalog.yaml" --factor 2
PYTHONPATH="$ROOT" nice -n 10 python3 -m tools.omr.training.train_yolo \
  --data "$CAT/catalog-2xdense.yaml" --weights "$PROD" \
  --epochs 1 --imgsz 896 --batch 8 --workers 2 --device mps --patience 99 \
  --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
  --extra-kwargs '{"save_period": 1}' --project "$ROOT/runs/2.4b" --name "$NAME"
ls -la "runs/2.4b/$NAME/weights/"
