#!/usr/bin/env bash
# Phase H — package everything the Vast.ai instance needs into a single
# tar.gz. Extract on the instance with:
#   mkdir -p /workspace/reengrave-training
#   tar -xzf phase-h-bundle.tar.gz -C /workspace/reengrave-training/
#   cd /workspace/reengrave-training
#   bash phase_h_remote_bootstrap.sh
set -euo pipefail

REPO_ROOT=${REPO_ROOT:-/Users/seanjohnson/Desktop/ReEngrave}
WORKTREE=${WORKTREE:-$REPO_ROOT/.claude/worktrees/interesting-curran-3ca1b7}
PHASE_H=$WORKTREE/benchmarks/omr-imslp-pipeline/phase-h-data
WEIGHTS=$REPO_ROOT/omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
TRAINING_SRC=$WORKTREE/tools/omr/training
SCRIPTS_SRC=$WORKTREE/benchmarks/omr-imslp-pipeline

OUT=${OUT:-$WORKTREE/benchmarks/omr-imslp-pipeline/phase-h-bundle.tar.gz}

STAGE=$(mktemp -d -t phase-h-bundle-XXXXXX)
trap "rm -rf $STAGE" EXIT

echo "Staging bundle in $STAGE ..."
mkdir -p "$STAGE/training" "$STAGE/data"

# Copy training scripts (Python module dir). Exclude the heavy local
# DSv2 data + runs/.
rsync -a --exclude 'data/deepscoresv2' --exclude 'data/deepscoresv2-yolo' \
      --exclude 'runs/' --exclude '__pycache__/' --exclude '*.pyc' \
      "$TRAINING_SRC/" "$STAGE/training/"

# Make sure deepscores_classes.py is at the module root (already there).

# Warm-start weights → training/data/weights/
mkdir -p "$STAGE/training/data/weights"
if [[ ! -f "$WEIGHTS" ]]; then
  echo "ERROR: prod weights not found at $WEIGHTS" >&2
  exit 2
fi
cp "$WEIGHTS" "$STAGE/training/data/weights/"

# Catalog images + labels + splits + yamls
mkdir -p "$STAGE/data"
rsync -a "$PHASE_H/" "$STAGE/data/phase-h-data/"

# Remote scripts (include both Phase H and Phase I launchers when present)
cp "$SCRIPTS_SRC/phase_h_remote_bootstrap.sh" "$STAGE/"
cp "$SCRIPTS_SRC/phase_h_launch_training.sh"  "$STAGE/"
[[ -f "$SCRIPTS_SRC/phase_i_launch_training.sh" ]] && \
  cp "$SCRIPTS_SRC/phase_i_launch_training.sh" "$STAGE/"
[[ -f "$SCRIPTS_SRC/phase_j_launch_training.sh" ]] && \
  cp "$SCRIPTS_SRC/phase_j_launch_training.sh" "$STAGE/"
[[ -f "$SCRIPTS_SRC/phase_j_mix_setup.sh" ]] && \
  cp "$SCRIPTS_SRC/phase_j_mix_setup.sh" "$STAGE/"
[[ -f "$SCRIPTS_SRC/phase_k_launch_training.sh" ]] && \
  cp "$SCRIPTS_SRC/phase_k_launch_training.sh" "$STAGE/"

# Sanity print
echo "Bundle contents:"
echo "  training:     $(find $STAGE/training -name '*.py' | wc -l) Python files, "\
"$(du -sh $STAGE/training | cut -f1) total"
echo "  weights:      $(ls -lh $STAGE/training/data/weights/*.pt | awk '{print $5, $9}')"
echo "  catalog imgs: $(find $STAGE/data/phase-h-data/images -name '*.png' | wc -l) files, "\
"$(du -sh $STAGE/data/phase-h-data/images | cut -f1)"
echo "  catalog lbls: $(find $STAGE/data/phase-h-data/labels -name '*.txt' | wc -l) files"
echo "  splits:       $(ls $STAGE/data/phase-h-data/*.txt $STAGE/data/phase-h-data/*.yaml)"
echo

echo "Tar+gzip → $OUT ..."
tar -czf "$OUT" -C "$STAGE" .
SZ=$(ls -lh "$OUT" | awk '{print $5}')
echo
echo "✓ wrote $OUT ($SZ)"
echo
echo "Ship it with:"
echo "  scp -P PORT $OUT root@HOST.vast.ai:/workspace/phase-h-bundle.tar.gz"
echo "Then on the instance:"
echo "  mkdir -p /workspace/reengrave-training"
echo "  tar -xzf /workspace/phase-h-bundle.tar.gz -C /workspace/reengrave-training/"
echo "  cd /workspace/reengrave-training"
echo "  bash phase_h_remote_bootstrap.sh"
echo "  tmux new -s train"
echo "  bash phase_h_launch_training.sh    # catalog-only (recommended, ~30 min)"
