#!/bin/bash
# Round 9 e2e chain: wait for the running scan anchor arm, then launch the
# anchor+cv scan arm, then the engraved anchor arm. Serial on purpose — the
# evals contend for MPS and CPU.
cd "$(dirname "$0")/../.." || exit 1
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python

while pgrep -f "scan_eval.py" > /dev/null; do sleep 60; done
echo "[chain] scan anchor arm done: $(date)"

bash benchmarks/omr-arc-anchor-2026-09/run_scan_arm.sh anchor+cv arcanchorcv
sleep 30
while pgrep -f "scan_eval.py" > /dev/null; do sleep 60; done
echo "[chain] scan anchor+cv arm done: $(date)"

export OMR_ARC_CV=anchor
python3 -m tools.omr.training.orchestral_eval --omr-ned \
  --out benchmarks/omr-arc-anchor-2026-09/results-engraved-arcanchor.json \
  > benchmarks/omr-arc-anchor-2026-09/engraved-arcanchor.log 2>&1
echo "[chain] engraved anchor arm done: $(date)"
