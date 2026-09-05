#!/bin/bash
# Launch the engraved (orchestral_eval) arm detached. Usage: run_engraved_arm.sh <mode> <tag>
cd "$(dirname "$0")/../.." || exit 1
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export OMR_ARC_CV="$1"
nohup python3 -m tools.omr.training.orchestral_eval --omr-ned \
  --out "benchmarks/omr-arc-cv-2026-09/results-engraved-$2.json" \
  > "benchmarks/omr-arc-cv-2026-09/engraved-$2.log" 2>&1 &
echo "launched pid $!"
