#!/usr/bin/env bash
# Run LEGATO OMR on page image(s) on a rented CUDA GPU box (vast.ai / RunPod).
# Emits one ABC-notation JSON per image. Bring those back to your Mac and diff
# them against the pipeline with:
#   python3 -m tools.omr.oemer_second_opinion --engine legato \
#       --omr-json <page>.omr.json --page 0 --legato-abc <stem>_..._abc.json
#
# Only the LEGATO inference runs here; the clef/time-sig diff runs locally on
# your Mac (CPU) — this box just turns a page image into ABC.
#
# Usage (on the GPU box):
#   bash run_on_gpu.sh page1.png [page2.png ...]
#
# Hardware: a CUDA GPU with ~14GB+ VRAM (fp16). First run downloads ~20GB of
# weights to ~/.cache/huggingface. A pytorch:2.6.0-cuda12.4 image is fastest
# (torch preinstalled) but any recent CUDA box works.
set -euo pipefail

MODEL="${LEGATO_MODEL:-guangyangmusic/legato}"   # or guangyangmusic/legato-small
WORK="${WORK:-$HOME/legato-run}"
OUT="${OUT:-$WORK/out}"
mkdir -p "$WORK" "$OUT"

if [ "$#" -lt 1 ]; then
  echo "usage: bash run_on_gpu.sh page1.png [page2.png ...]" >&2
  exit 2
fi

# 1. LEGATO repo
if [ ! -d "$WORK/legato" ]; then
  git clone --depth 1 https://github.com/guang-yng/legato "$WORK/legato"
fi

# 2. Python env — inference subset only (skip deepspeed / wandb / musicdiff,
#    which are train/eval-only and the SSH-git musicdiff dep needs a key).
python3 -m venv "$WORK/venv"
# shellcheck disable=SC1091
source "$WORK/venv/bin/activate"
pip install -q --upgrade pip
pip install -q torch==2.6.0 transformers==4.54.0 accelerate==1.8.0 \
    datasets==3.2.0 pillow==11.1.0 numpy==1.26.4 fire tqdm huggingface_hub

# 3. Inference (weights auto-download on first from_pretrained call)
cd "$WORK/legato"
for img in "$@"; do
  echo ">>> LEGATO on $img"
  PYTHONPATH="$WORK/legato" python scripts/inference.py \
    --model_path "$MODEL" --image_path "$(readlink -f "$img")" \
    --output_path "$OUT" --device cuda --fp16
done

echo ">>> Done. ABC JSON(s):"
ls -la "$OUT"
echo ">>> Download the *_abc.json file(s) to your Mac, then run the bridge with --legato-abc."
