#!/usr/bin/env bash
# Re-gate a round-3 checkpoint on BOTH axes, because they DISAGREED last time.
#
# The 30-epoch cloud run (p29) WON the narrow axis — scanned half-notes 27 -> 35,
# with-duration recall 0.435 -> 0.605 — and LOST the broad one: 5-page scan-e2e
# pooled OMR-NED 0.7512 -> 0.7761, because it detected fewer rests and
# accidentals. Gating on the narrow axis alone would have shipped that.
# So: ship only if the half-note gain holds AND scan-e2e does not regress.
#
#   ./run_gate_round3.sh <ckpt.pt> [tag]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$ROOT"
CKPT="${1:?usage: run_gate_round3.sh <checkpoint.pt> [tag]}"
TAG="${2:-r3}"
MAIN=/Users/seanjohnson/Desktop/ReEngrave
PROD="$MAIN/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
BEET5="$MAIN/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"

# ⚠️ ABSOLUTE paths for BOTH arms. DEFAULT_WEIGHTS is repo-relative AND the file
# is gitignored, so in a worktree the baseline arm silently reads nothing.
export OMRNED_PYTHON="$MAIN/.venv-omrned/bin/python"

echo "############ AXIS 1 — forgetting + hollow payoff (beet5 p1) ############"
python3 benchmarks/omr-labeling-survey-2026-09/gate_all.py \
    --prod "$PROD" --ckpt "${TAG}=${CKPT}" --beet5-pdf "$BEET5" --page 1

echo
echo "############ AXIS 2 — 5-page scan-e2e, full-symbol OMR-NED ############"
echo "# production baseline (already measured under --tag prodbase if present)"
OMR_SCAN_EVAL_WEIGHTS="$CKPT" python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py \
    --tag "$TAG" --out "/tmp/scan_${TAG}.json"
echo
echo "compare /tmp/scan_prod.json  vs  /tmp/scan_${TAG}.json — pooled OMR-NED, lower is better."
echo "SHIP ONLY IF BOTH HOLD."
