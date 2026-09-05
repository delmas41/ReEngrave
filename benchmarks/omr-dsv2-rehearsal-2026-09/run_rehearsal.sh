#!/usr/bin/env bash
# DSv2-rehearsal training. Runs ON THE RENTED BOX (tmux). Two arms, one mix.
#
#   ./run_rehearsal.sh data     # download + extract + prepare DSv2, build mix
#   ./run_rehearsal.sh train    # both arms + strip + checksums
#   ./run_rehearsal.sh all      # everything (default)
#
# Round-5 recipe throughout (run_method_sweep.sh): imgsz 896, batch 16,
# patience 99, music-aug zeros, save_period=1, nc=208 (never
# --allow-nc-expansion — an nc mismatch silently re-initializes the head).
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH="$(pwd)"

RATIO="${RATIO:-3}"
EPOCHS="${EPOCHS:-5}"
IMGSZ="${IMGSZ:-896}"
BATCH="${BATCH:-16}"
BASE_W="weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
PROD_W="weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
STEP="${1:-all}"

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

if [ "$STEP" = all ] || [ "$STEP" = data ]; then
  echo "== [1/4] DSv2 dense download (idempotent) =="
  python3 -m tools.omr.training.download_dataset --out data/deepscoresv2
  echo "== [2/4] extract =="
  if [ ! -f data/deepscoresv2/.extracted ]; then
    tar xzf data/deepscoresv2/ds2_dense.tar.gz -C data/deepscoresv2
    touch data/deepscoresv2/.extracted
  fi
  SRC="$(dirname "$(find data/deepscoresv2 -maxdepth 3 -name deepscores_train.json | head -1)")"
  if [ -z "$SRC" ] || [ "$SRC" = "." ]; then
    echo "ABORT: deepscores_train.json not found under data/deepscoresv2 — layout differs:" >&2
    find data/deepscoresv2 -maxdepth 2 | head -30 >&2
    exit 2
  fi
  echo "DSV2 SRC=$SRC"
  echo "== [3/4] YOLO-format conversion =="
  if [ ! -f data/deepscoresv2-yolo/data.yaml ]; then
    python3 -m tools.omr.training.prepare_yolo_data \
      --src "$SRC" --dst data/deepscoresv2-yolo
  fi
  echo "== [4/4] the mixed dataset (ratio ${RATIO}:1 DSv2:scan) =="
  python3 build_mix.py --ratio "$RATIO"
fi

train_arm () {
  local NAME="$1" W="$2"
  echo "===== ARM $NAME  from $W  imgsz=$IMGSZ batch=$BATCH epochs=$EPOCHS"
  python3 -m tools.omr.training.train_yolo \
    --data mix/data.yaml --weights "$W" \
    --epochs "$EPOCHS" --imgsz "$IMGSZ" --batch "$BATCH" --device 0 --patience 99 \
    --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
    --extra-kwargs '{"save_period": 1}' \
    --project runs --name "$NAME"
  ls -la "runs/$NAME/weights/" || true
}

if [ "$STEP" = all ] || [ "$STEP" = train ]; then
  train_arm rehbase "$BASE_W"
  train_arm rehprod "$PROD_W"

  # Strip the optimizer state before transfer (round-5 lesson: ~350 MB ->
  # ~88 MB each; sizes printed so a truncated transfer is visible on arrival).
  python3 - <<'PYSTRIP'
import glob
from ultralytics.utils.torch_utils import strip_optimizer
for f in sorted(glob.glob("runs/*/weights/*.pt")):
    try:
        strip_optimizer(f)
    except Exception as exc:
        print("strip failed", f, exc)
PYSTRIP
  echo "== checkpoints (all should be ~88 MB — a smaller one is truncated):"
  ls -la runs/*/weights/*.pt
  md5sum runs/*/weights/*.pt | tee runs/CHECKSUMS.md5
fi
echo "== DONE ($STEP)"
