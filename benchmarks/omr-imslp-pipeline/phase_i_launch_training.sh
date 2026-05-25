#!/usr/bin/env bash
# Phase I — catalog-augmented fine-tune with the music-start anchored
# labels. Same proven Phase 3.4 v1b config (SGD lr0=0.0005, no mosaic)
# that preserved WTC F1 within 0.3 pts on a smaller fine-tune set.
#
# Run in tmux on the Vast.ai instance so it survives SSH disconnects:
#   tmux new -s train
#   bash phase_i_launch_training.sh
#   # detach: Ctrl-b d
#   # reattach: tmux attach -t train
set -euo pipefail

ROOT=${ROOT:-/workspace/reengrave-training}
DATA_BASE=${DATA_BASE:-$ROOT/data}
PHASE_H=$DATA_BASE/phase-h-data
WEIGHTS=${WEIGHTS:-$ROOT/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt}

if [[ ! -f "$WEIGHTS" ]]; then
  echo "ERROR: warm-start weights not found at $WEIGHTS" >&2
  exit 2
fi

DATA_YAML=$PHASE_H/data-catalog-only.yaml
if [[ ! -f "$DATA_YAML" ]]; then
  echo "ERROR: data yaml not found at $DATA_YAML" >&2
  exit 2
fi

NAME=phase-i-fixed-offset
LOGDIR=$ROOT/runs/$NAME
mkdir -p "$LOGDIR"
LOG=$LOGDIR/$(date -u +%Y%m%dT%H%M%S)-train.log
echo "Phase I training: yaml=$DATA_YAML  log=$LOG"

# Phase 3.4 v1b proven config — preserves WTC F1.
#   * SGD optimizer with very low learning rate
#   * no rotation / flips / hue-sat
#   * no mosaic (catalog images are already complete pages)
#   * short warmup
cd "$ROOT"
python3 -m training.train_yolo \
  --data "$DATA_YAML" \
  --weights "$WEIGHTS" \
  --epochs 30 \
  --patience 5 \
  --batch 4 \
  --imgsz 1280 \
  --device 0 \
  --workers 4 \
  --project "$ROOT/runs" \
  --name "$NAME" \
  --fliplr 0 --flipud 0 \
  --hsv_h 0 --hsv_s 0 --hsv_v 0.4 \
  --mosaic 0 \
  --degrees 1 \
  --extra-kwargs '{"optimizer":"SGD","lr0":0.0005,"momentum":0.937,"warmup_epochs":1,"close_mosaic":0}' \
  2>&1 | tee "$LOG"

echo
echo "Best weights: $ROOT/runs/$NAME/weights/best.pt"
echo "Last weights: $ROOT/runs/$NAME/weights/last.pt"
ls -la "$ROOT/runs/$NAME/weights/" 2>/dev/null || true
