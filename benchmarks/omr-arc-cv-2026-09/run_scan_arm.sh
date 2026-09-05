#!/bin/bash
# Launch one scan-e2e arm detached. Usage: run_scan_arm.sh <mode> <tag>
cd "$(dirname "$0")/../.." || exit 1
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export OMR_ARC_CV="$1"
export OMR_SCAN_EVAL_WEIGHTS=/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
nohup python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --wait-for-cpu \
  --tag "$2" --out "benchmarks/omr-arc-cv-2026-09/results-scan-$2.json" \
  > "benchmarks/omr-arc-cv-2026-09/scan-$2.log" 2>&1 &
echo "launched pid $!"
