#!/usr/bin/env bash
# Phase J — mix mode setup on the Vast.ai instance.
#
# Run after phase_h_remote_bootstrap.sh:
#   1. Downloads DSv2 dense subset (~5-7 GB)
#   2. Extracts → data/deepscoresv2/
#   3. Converts annotations → data/deepscoresv2-yolo/ (YOLO format)
#   4. Builds combined train list (DSv2 + catalog) + data-j-mix.yaml
#
# Idempotent: re-runnable if anything fails mid-setup.
set -euo pipefail

ROOT=${ROOT:-/workspace/reengrave-training}
DATA_BASE=${DATA_BASE:-$ROOT/data}
DSV2_RAW=$DATA_BASE/deepscoresv2
DSV2_YOLO=$DATA_BASE/deepscoresv2-yolo
PHASE_H=$DATA_BASE/phase-h-data

echo "== Phase J mix setup =="
echo "  ROOT      = $ROOT"
echo "  DATA_BASE = $DATA_BASE"

# ── 1. Download DSv2 dense subset ────────────────────────────────────────────
if [[ ! -f $DSV2_RAW/ds2_dense.tar.gz && ! -d $DSV2_RAW/images ]]; then
  mkdir -p "$DSV2_RAW"
  echo "Downloading ds2_dense.tar.gz (~5-7 GB) ..."
  curl -L --retry 3 --retry-delay 2 \
    -o "$DSV2_RAW/ds2_dense.tar.gz" \
    "https://zenodo.org/records/4012193/files/ds2_dense.tar.gz"
fi

# ── 2. Extract if needed ─────────────────────────────────────────────────────
if [[ ! -d "$DSV2_RAW/images" ]]; then
  echo "Extracting ds2_dense.tar.gz ..."
  cd "$DSV2_RAW"
  tar -xzf ds2_dense.tar.gz
  # Some DSv2 tarballs have a top-level "ds2_dense/" wrapper. Flatten.
  if [[ -d "ds2_dense" && ! -d "images" ]]; then
    mv ds2_dense/* . 2>/dev/null || true
    rmdir ds2_dense 2>/dev/null || true
  fi
  cd -
fi

echo "DSv2 raw contents:"
ls "$DSV2_RAW/" | head -20

# ── 3. Convert annotations to YOLO format ───────────────────────────────────
if [[ ! -d "$DSV2_YOLO/images" || ! -d "$DSV2_YOLO/labels" ]]; then
  echo "Converting DSv2 annotations → YOLO format ..."
  cd "$ROOT"
  python3 -m training.prepare_yolo_data \
    --src "$DSV2_RAW" --dst "$DSV2_YOLO"
fi
echo "DSv2 YOLO conversion done:"
ls "$DSV2_YOLO/" | head -10
N_DSV2_IMG=$(find "$DSV2_YOLO/images" -name "*.png" -o -name "*.jpg" | wc -l)
N_DSV2_LBL=$(find "$DSV2_YOLO/labels" -name "*.txt" | wc -l)
echo "DSv2 images: $N_DSV2_IMG  labels: $N_DSV2_LBL"

# ── 4. Build combined train list + data-j-mix.yaml ───────────────────────────
echo "Building combined train list ..."

# Catalog train.txt has paths like: $DATA_BASE/phase-h-data/images/.../p###.png
# DSv2 images live at: $DSV2_YOLO/images/dense/*.png
# Concatenate and shuffle.

CAT_TRAIN=$PHASE_H/train.txt
DSV2_TRAIN_LIST=$PHASE_H/train.dsv2.txt
MIX_TRAIN=$PHASE_H/train.j-mix.txt

if [[ ! -f "$CAT_TRAIN" ]]; then
  echo "ERROR: catalog train.txt not found at $CAT_TRAIN" >&2
  exit 2
fi

find "$DSV2_YOLO/images" -name "*.png" -o -name "*.jpg" | sort > "$DSV2_TRAIN_LIST"
N_DSV2=$(wc -l < "$DSV2_TRAIN_LIST")
N_CAT=$(wc -l < "$CAT_TRAIN")
echo "DSv2 images: $N_DSV2  Catalog images: $N_CAT"

# Upsample catalog so it's not drowned in DSv2. Target: catalog ≈ 20% of mix.
# upsample_ratio = round(0.20 * N_DSV2 / (0.80 * N_CAT))
if (( N_CAT > 0 )); then
  REPEAT=$(( (N_DSV2 / 4) / N_CAT ))
  (( REPEAT < 1 )) && REPEAT=1
else
  REPEAT=1
fi
echo "Upsampling catalog by ${REPEAT}x so it's ~20% of mix"

> "$MIX_TRAIN"
for ((i=0; i<REPEAT; i++)); do
  cat "$CAT_TRAIN" >> "$MIX_TRAIN"
done
cat "$DSV2_TRAIN_LIST" >> "$MIX_TRAIN"
# Shuffle in-place (gnu shuf available on Vast.ai's ubuntu image).
shuf -o "$MIX_TRAIN" "$MIX_TRAIN"
N_MIX=$(wc -l < "$MIX_TRAIN")
echo "Mix train list: $N_MIX lines (catalog upsampled ${REPEAT}x + DSv2)"

# Build data-j-mix.yaml — same nc + names as catalog-only, just different
# train/val. Val stays catalog-only (the catalog has the labels we care
# about validating — DSv2's full label set would just be background here).
sed -e "s|train: .*|train: train.j-mix.txt|" "$PHASE_H/data-catalog-only.yaml" \
  > "$PHASE_H/data-j-mix.yaml"
echo "Wrote $PHASE_H/data-j-mix.yaml"
head -5 "$PHASE_H/data-j-mix.yaml"

touch /workspace/mix-setup.done
echo "✓ Phase J mix setup complete"
