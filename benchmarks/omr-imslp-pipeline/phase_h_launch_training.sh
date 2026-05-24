#!/usr/bin/env bash
# Phase H — launch the catalog-augmented fine-tune.
#
# Two modes:
#   (default)   catalog-only: 30 epochs on the ~400-image catalog train set
#               (warm-start from prod weights, lr0=0.001 to prevent
#               catastrophic forgetting). ~20-40 min wall time on A100.
#   --mix       catalog + DSv2 (full handoff plan): combined train set
#               = DSv2 train (~165k) + catalog upsampled 200x (~80k).
#               ~5-12 hours on A100.
#
# Run in tmux so it survives SSH disconnects:
#   tmux new -s train
#   bash phase_h_launch_training.sh
#   # detach: Ctrl-b d
#   # reattach: tmux attach -t train
set -euo pipefail

MODE=${1:-catalog-only}   # accepts --mix or "mix" or "catalog-only"
case "$MODE" in
  --mix|mix)  MODE=mix ;;
  *)          MODE=catalog-only ;;
esac

ROOT=${ROOT:-/workspace/reengrave-training}
DATA_BASE=${DATA_BASE:-$ROOT/data}
PHASE_H=$DATA_BASE/phase-h-data
WEIGHTS=${WEIGHTS:-$ROOT/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt}

if [[ ! -f "$WEIGHTS" ]]; then
  echo "ERROR: warm-start weights not found at $WEIGHTS" >&2
  exit 2
fi

NAME=ds2-yolov8l-catalog-mix-ft
DATA_YAML=$PHASE_H/data-catalog-only.yaml
if [[ "$MODE" == "mix" ]]; then
  DATA_YAML=$PHASE_H/data-catalog-mix.yaml
  if [[ ! -f "$PHASE_H/train.mix.txt" ]]; then
    echo "ERROR: --mix mode requires $PHASE_H/train.mix.txt (run bootstrap)" >&2
    exit 2
  fi
fi

# Default batch=4 (fits 24GB RTX 4090). Override BATCH=6 on 40GB A100.
BATCH=${BATCH:-4}

LOGDIR=$ROOT/runs/phase-h
mkdir -p "$LOGDIR"
LOG=$LOGDIR/$(date -u +%Y%m%dT%H%M%S)-$MODE.log
echo "Phase H training: mode=$MODE  yaml=$DATA_YAML  batch=$BATCH  log=$LOG"

# Use the project's train_yolo.py so flag handling is consistent.
# cd $ROOT (not $ROOT/training) so `python3 -m training.X` finds the module.
cd "$ROOT"
python3 -m training.train_yolo \
  --data "$DATA_YAML" \
  --weights "$WEIGHTS" \
  --epochs 30 \
  --patience 10 \
  --batch "$BATCH" \
  --imgsz 1280 \
  --device 0 \
  --workers 8 \
  --project "$LOGDIR" \
  --name "$NAME" \
  --fliplr 0 --flipud 0 \
  --hsv_h 0 --hsv_s 0 --hsv_v 0.4 \
  --mosaic 0.5 \
  --degrees 2 \
  --extra-kwargs '{"lr0": 0.001, "warmup_epochs": 2, "cls": 1.0}' \
  2>&1 | tee "$LOG"

echo
echo "Best weights: $LOGDIR/$NAME/weights/best.pt"
ls -la "$LOGDIR/$NAME/weights/" 2>/dev/null || true
