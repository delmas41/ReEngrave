#!/usr/bin/env bash
# Cloud (CUDA) training for the Phase-2 hollow re-ship at the PROPER imgsz-2048
# recipe. Runs ON THE RENTED BOX after the tarball is extracted. Fine-tunes from
# the PRE-hollow 2048 base checkpoint (the clean native-scale base the 896 ship
# only approximated); the result is compared LOCALLY against current production
# (deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt).
#
# Usage:  ./run_cloud_training.sh [primary|ablation]
#   primary  = v1-4 dense + v7,v8 (Phase-1 hollow) + v9,v10,v11 (Phase-2 clean)   <- SHIP candidate
#   ablation = primary + v12 (Tchaikovsky low-res)  <- MEASURE whether low-res helps or hurts
# Env knobs: IMGSZ(2048) BATCH(4) EPOCHS(10) FACTOR(3)
set -euo pipefail

MIX="${1:-primary}"
IMGSZ="${IMGSZ:-2048}"
BATCH="${BATCH:-4}"
EPOCHS="${EPOCHS:-10}"
FACTOR="${FACTOR:-3}"
BASE_W="weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
export PYTHONPATH="$(pwd)"

DENSE="v1-2026-05-18-orchestral v2-2026-06-08-beet5 v3-2026-06-09-mahler5 v4-2026-06-10-la-mer"
HOLLOW="v7-2026-09-02-hollow v8-2026-09-02-hollow2-5pub v9-2026-09-03-hollow3-mahler1 v10-2026-09-03-hollow3-elgar1 v11-2026-09-03-hollow3-lamer"
TCHAIK="v12-2026-09-03-hollow3-tchaikovsky1-lowres"

VERSIONS="$DENSE $HOLLOW"
[ "$MIX" = "ablation" ] && VERSIONS="$VERSIONS $TCHAIK"

echo "== MIX=$MIX  IMGSZ=$IMGSZ BATCH=$BATCH EPOCHS=$EPOCHS FACTOR=$FACTOR =="
echo "== versions: $VERSIONS"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

ROOT="catalog-$MIX"
rm -rf "$ROOT"; mkdir -p "$ROOT"
for v in $VERSIONS; do ln -sfn "$(pwd)/data/user-labeled/$v" "$ROOT/$v"; done

# 1. build the nc=208 catalog (fallback class-names => no torch needed here)
python3 -m tools.omr.training.build_catalog_yaml \
  --root "$ROOT" --versions $VERSIONS \
  --fallback-class-names tools/omr/training/deepscoresv2_208_classes.json

# 2. oversample the dense base FACTOR x (hollow stays a clear minority)
python3 oversample_dense.py --catalog "$ROOT/catalog.yaml" --factor "$FACTOR"

# 3. fine-tune from the 2048 base, per-epoch checkpoints, music-aware aug, nc=208
#    (NO --allow-nc-expansion: nc must stay 208 to avoid the Phase-3.4 head reset)
python3 -m tools.omr.training.train_yolo \
  --data "$ROOT/catalog-${FACTOR}xdense.yaml" \
  --weights "$BASE_W" \
  --epochs "$EPOCHS" --imgsz "$IMGSZ" --batch "$BATCH" --device 0 --patience 20 \
  --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
  --extra-kwargs '{"save_period": 1}' \
  --project runs --name "cloud-${IMGSZ}-${MIX}"

echo "== DONE. Checkpoints (epoch0.pt, epoch1.pt, ... best.pt, last.pt) in:"
ls -la runs/cloud-${IMGSZ}-${MIX}/weights/ 2>/dev/null || \
  find runs -name '*.pt' -newer "$BASE_W" 2>/dev/null
echo "== scp the epoch*.pt back to the Mac for the local re-gate."
