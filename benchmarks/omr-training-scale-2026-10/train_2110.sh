#!/usr/bin/env bash
# ROADMAP 2.110 Step B -- ONE 1-epoch fine-tune from PRODUCTION; ARM=old (imgsz 896, the 2.4b CONTROL recipe on the filtered list)
# or ARM=matched (cells pre-resized to staff space 16 on a 640 canvas, imgsz 640). Everything else identical: same flags as train_2.4b.sh
# (batch 8 / workers 2 / mps / nice 10 / fliplr 0 flipud 0 hsv_h 0 hsv_s 0 / default mosaic + scale aug), seed 0, 1 epoch, save_period 1.
# Build the datasets first: build_arms.py.  One training at a time: lock file + trap like train_2.4b.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ROOT="$(pwd)"
ARM="${ARM:?ARM=old|matched}"
LOCK=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/.training-2.110.lock
PROD=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
case "$ARM" in old) IMGSZ=896;; matched) IMGSZ=640;; *) echo bad ARM; exit 2;; esac
trap 'rm -f "$LOCK"' EXIT INT TERM
echo "2.110 $ARM pid $$ $(date -u +%FT%TZ)" > "$LOCK"
PYTHONPATH="$ROOT" nice -n 10 python3 -m tools.omr.training.train_yolo \
  --data "runs/2.110/$ARM/catalog.yaml" --weights "$PROD" \
  --epochs 1 --imgsz "$IMGSZ" --batch 8 --workers 2 --device mps --patience 99 \
  --fliplr 0 --flipud 0 --hsv_h 0 --hsv_s 0 \
  --extra-kwargs '{"save_period": 1, "seed": 0}' --project "$ROOT/runs/2.110/train" --name "$ARM"
ls -la "runs/2.110/train/$ARM/weights/"
