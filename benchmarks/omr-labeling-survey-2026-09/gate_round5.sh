#!/usr/bin/env bash
# Gate a round-5 checkpoint on all THREE axes, cheapest-discriminator first.
#
#   ./gate_round5.sh <ckpt.pt> <tag>
#
# Axis 3 (class-space survival) runs FIRST because it is free once axis 2 has
# written the raw JSON, and because it is the axis that separates the round-3/4
# candidates from production at a glance: they hold noteheads and lose sixteen
# other classes. Axis 2 is the pooled OMR-NED, which is symmetric and therefore
# FLATTERS a model that predicts less — never read it without axis 3 beside it.
# Axis 1 is the narrow hollow-notehead payoff, which every candidate so far wins
# and which alone would have shipped two regressions.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$ROOT"
CKPT="${1:?usage: gate_round5.sh <checkpoint.pt> <tag>}"
TAG="${2:?usage: gate_round5.sh <checkpoint.pt> <tag>}"
MAIN=/Users/seanjohnson/Desktop/ReEngrave
PROD="$MAIN/omr-weights/deepscoresv2-yolov8l-hollow-ft-2026-09-03.pt"
BEET5="$MAIN/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
export OMRNED_PYTHON="$MAIN/.venv-omrned/bin/python"
SURVEY=benchmarks/omr-labeling-survey-2026-09

echo "######## AXIS 2 — 5-page scan-e2e, full-symbol OMR-NED ########"
OMR_SCAN_EVAL_WEIGHTS="$CKPT" python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py \
    --tag "$TAG" --out "benchmarks/omr-scan-e2e-2026-09/results-round5-${TAG}.json"

echo
echo "######## AXIS 3 — class-space survival vs production ########"
python3 "$SURVEY/probe_confidence_shift.py" --arms prodbase "$TAG" --gate prodbase \
    > "/tmp/classgate_${TAG}.json" || echo "  (axis 3 FAILED — see above)"
tail -5 "/tmp/classgate_${TAG}.json" >/dev/null 2>&1 || true

echo
echo "######## AXIS 1 — forgetting + hollow payoff (beet5 p1) ########"
python3 "$SURVEY/gate_all.py" --prod "$PROD" --ckpt "${TAG}=${CKPT}" \
    --beet5-pdf "$BEET5" --page 1

echo
echo "SHIP ONLY IF ALL THREE HOLD."
