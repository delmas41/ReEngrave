#!/usr/bin/env bash
# Phase J — fine-tune prod weights on structural-only catalog labels.
#
# Labels emit only barlines (class 207), stems (class 41), beams (class 121).
# Other prod classes (noteheads, clefs, etc.) are NOT in the catalog labels.
#
# Configurable via env or flags:
#   MODE=catalog-only (default) | mix
#   FREEZE=N           freeze first N layers of backbone (default 0)
#   LR0=0.0005         initial LR (default Phase 3.4 v1b)
#
# Mix mode requires DSv2 to be downloaded already (deepscoresv2-yolo/)
# and a data-mix.yaml that points to both label sets.
set -euo pipefail

MODE=${MODE:-catalog-only}
FREEZE=${FREEZE:-0}
LR0=${LR0:-0.0005}

ROOT=${ROOT:-/workspace/reengrave-training}
DATA_BASE=${DATA_BASE:-$ROOT/data}
PHASE_H=$DATA_BASE/phase-h-data
WEIGHTS=${WEIGHTS:-$ROOT/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt}

if [[ ! -f "$WEIGHTS" ]]; then
  echo "ERROR: warm-start weights not found at $WEIGHTS" >&2
  exit 2
fi

DATA_YAML=$PHASE_H/data-catalog-only.yaml
if [[ "$MODE" == "mix" ]]; then
  DATA_YAML=$PHASE_H/data-catalog-mix.yaml
  if [[ ! -f "$DATA_YAML" ]]; then
    echo "ERROR: mix mode requires $DATA_YAML" >&2
    exit 2
  fi
fi
if [[ ! -f "$DATA_YAML" ]]; then
  echo "ERROR: data yaml not found at $DATA_YAML" >&2
  exit 2
fi

NAME=phase-j-$MODE
[[ "$FREEZE" -gt 0 ]] && NAME="$NAME-freeze$FREEZE"
LOGDIR=$ROOT/runs/$NAME
mkdir -p "$LOGDIR"
LOG=$LOGDIR/$(date -u +%Y%m%dT%H%M%S)-train.log
echo "Phase J: mode=$MODE freeze=$FREEZE lr0=$LR0  yaml=$DATA_YAML  log=$LOG"

EXTRA_ARGS=()
if [[ "$FREEZE" -gt 0 ]]; then
  EXTRA_ARGS+=(--freeze "$FREEZE")
fi

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
  "${EXTRA_ARGS[@]}" \
  --extra-kwargs "{\"optimizer\":\"SGD\",\"lr0\":$LR0,\"momentum\":0.937,\"warmup_epochs\":1,\"close_mosaic\":0}" \
  2>&1 | tee "$LOG"

echo
echo "Best weights: $ROOT/runs/$NAME/weights/best.pt"
ls -la "$ROOT/runs/$NAME/weights/" 2>/dev/null || true
