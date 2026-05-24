#!/usr/bin/env bash
# Phase H — remote bootstrap to be run ON the Vast.ai instance after
# scp-ing phase-h-bundle.tar.gz to /workspace/.
#
# Idempotent: re-runnable if anything fails mid-setup.
#
# Usage (on the instance):
#   bash phase_h_remote_bootstrap.sh
#
# What it does:
#   1. Extract the bundle (if not already).
#   2. Install pip dependencies (torch from PyTorch CUDA wheel, ultralytics).
#   3. Substitute {DATA_BASE} in the data yamls and txt files.
#   4. (Mix mode only) concatenate DSv2 train.txt + catalog train.repeated.txt
#      → train.mix.txt. Skipped for catalog-only mode.
#   5. Print a final layout sanity check.
set -euo pipefail

BUNDLE=${BUNDLE:-/workspace/phase-h-bundle.tar.gz}
ROOT=${ROOT:-/workspace/reengrave-training}
DATA_BASE=${DATA_BASE:-$ROOT/data}

echo "== Phase H remote bootstrap =="
echo "  BUNDLE    = $BUNDLE"
echo "  ROOT      = $ROOT"
echo "  DATA_BASE = $DATA_BASE"

# ── 1. Extract bundle ────────────────────────────────────────────────────────
mkdir -p "$ROOT"
if [[ ! -d "$ROOT/training" ]]; then
  if [[ ! -f "$BUNDLE" ]]; then
    echo "ERROR: bundle not found at $BUNDLE" >&2
    echo "scp the bundle first: scp -P PORT phase-h-bundle.tar.gz root@HOST:/workspace/" >&2
    exit 2
  fi
  echo "Extracting $BUNDLE → $ROOT ..."
  tar -xzf "$BUNDLE" -C "$ROOT"
fi

# ── 2. Pip deps ──────────────────────────────────────────────────────────────
if ! python3 -c "import torch; assert torch.cuda.is_available()" 2>/dev/null; then
  echo "Installing torch + ultralytics ..."
  pip3 install --break-system-packages --quiet --index-url https://download.pytorch.org/whl/cu124 torch torchvision || true
fi
pip3 install --break-system-packages --quiet ultralytics opencv-python-headless PyMuPDF lxml pyyaml || true
python3 -c "from ultralytics import YOLO; import torch; print('CUDA:', torch.cuda.is_available(), 'devices:', torch.cuda.device_count())"

# ── 3. Substitute {DATA_BASE} placeholders ───────────────────────────────────
PHASE_H=$DATA_BASE/phase-h-data
DSV2_BASE=$DATA_BASE/deepscoresv2-yolo
if [[ ! -d "$PHASE_H" ]]; then
  echo "ERROR: $PHASE_H not found after extract" >&2
  exit 2
fi
for f in "$PHASE_H"/train.txt "$PHASE_H"/val.txt "$PHASE_H"/train.repeated.txt \
         "$PHASE_H"/data-catalog-only.yaml "$PHASE_H"/data-catalog-mix.yaml; do
  if [[ -f "$f" ]]; then
    sed -i.bak "s|{DATA_BASE}|$DATA_BASE|g" "$f"
    rm -f "$f.bak"
  fi
done

# ── 4. (Mix mode) download DSv2 if needed, then build train.mix.txt ─────────
WANT_MIX=${WANT_MIX:-1}   # set WANT_MIX=0 to skip DSv2 download entirely
if [[ "$WANT_MIX" == "1" ]]; then
  if [[ ! -f "$DSV2_BASE/train.txt" ]]; then
    echo
    echo "== DSv2 download + prep (mix mode) =="
    mkdir -p "$DATA_BASE/deepscoresv2"
    cd "$ROOT"   # so `python3 -m training.X` resolves
    if [[ ! -f "$DATA_BASE/deepscoresv2/ds2_complete.tar.gz" && ! -d "$DATA_BASE/deepscoresv2/ds2_complete" ]]; then
      echo "Downloading full DSv2 (~75 GB compressed) ..."
      python3 -m training.download_dataset --full --out "$DATA_BASE/deepscoresv2/"
    fi
    if [[ ! -d "$DATA_BASE/deepscoresv2/ds2_complete" ]]; then
      echo "Extracting DSv2 ..."
      tar -xzf "$DATA_BASE/deepscoresv2/ds2_complete.tar.gz" -C "$DATA_BASE/deepscoresv2/"
    fi
    if [[ ! -d "$DSV2_BASE" ]]; then
      echo "Preparing YOLO-format split ..."
      python3 -m training.prepare_yolo_data \
        --src "$DATA_BASE/deepscoresv2/ds2_complete" \
        --dst "$DSV2_BASE"
    fi
    # prepare_yolo_data writes images/train + labels/train but no train.txt.
    # Generate them so the mix yaml can cat-concat.
    if [[ -d "$DSV2_BASE/images/train" && ! -f "$DSV2_BASE/train.txt" ]]; then
      find "$DSV2_BASE/images/train" -name "*.png" | sort > "$DSV2_BASE/train.txt"
      find "$DSV2_BASE/images/val"   -name "*.png" | sort > "$DSV2_BASE/val.txt"
      echo "DSv2 train.txt: $(wc -l < $DSV2_BASE/train.txt) lines"
      echo "DSv2 val.txt:   $(wc -l < $DSV2_BASE/val.txt) lines"
    fi
  fi
  if [[ -f "$DSV2_BASE/train.txt" ]]; then
    echo "Found DSv2 train.txt — building train.mix.txt for mix mode"
    cat "$DSV2_BASE/train.txt" "$PHASE_H/train.repeated.txt" > "$PHASE_H/train.mix.txt"
    wc -l "$PHASE_H/train.mix.txt"
  else
    echo "WARNING: DSv2 still missing — mix mode unavailable. Fall back to catalog-only."
  fi
fi

# ── 5. Layout sanity check ───────────────────────────────────────────────────
echo
echo "== Layout =="
echo "  Phase H images: $(find $PHASE_H/images -name '*.png' | wc -l)"
echo "  Phase H labels: $(find $PHASE_H/labels -name '*.txt' | wc -l)"
echo "  train.txt:      $(wc -l < $PHASE_H/train.txt) lines"
echo "  val.txt:        $(wc -l < $PHASE_H/val.txt) lines"
echo "  weights:        $(ls -lh $ROOT/training/data/weights/*.pt 2>/dev/null | awk '{print $5, $9}')"

# Resolve a few paths so we know they exist
head -3 "$PHASE_H/train.txt" | while read p; do
  [[ -f "$p" ]] && echo "  ok: $p" || echo "  MISSING: $p"
done

echo
echo "✓ Bootstrap complete. Next:"
echo "  bash $ROOT/training/phase_h_launch_training.sh          # catalog-only (fast)"
echo "  bash $ROOT/training/phase_h_launch_training.sh --mix    # catalog + DSv2 (long)"
