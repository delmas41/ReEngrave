#!/usr/bin/env bash
# Cheap first pass over a fleet of candidate checkpoints: ONE scan page each,
# scored only on class-space survival (gate axis 3).
#
# The full three-axis gate is ~15 minutes a checkpoint and a save_period=1 sweep
# produces dozens, so gating them all would cost a day. Axis 3 needs one page
# and separates every round-3/4 candidate from production at a glance — they
# hold noteheads and lose sixteen other classes — so it is the right screen.
# A checkpoint that passes here still has to clear the real gate.
#
#   ./screen_round5.sh <dir-of-checkpoints>
#   ./screen_round5.sh <ckpt.pt> [<ckpt.pt> ...]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$ROOT"
MAIN=/Users/seanjohnson/Desktop/ReEngrave
export OMRNED_PYTHON="$MAIN/.venv-omrned/bin/python"
ROW=beethoven-sym5-mvt1-984073-p1
SURVEY=benchmarks/omr-labeling-survey-2026-09

CKPTS=()
for a in "$@"; do
  if [ -d "$a" ]; then while IFS= read -r f; do CKPTS+=("$f"); done < <(find "$a" -name '*.pt' | sort)
  else CKPTS+=("$a"); fi
done
[ ${#CKPTS[@]} -eq 0 ] && { echo "usage: screen_round5.sh <dir|ckpt...>" >&2; exit 2; }

TAGS=()
for c in "${CKPTS[@]}"; do
  tag="scr$(basename "$(dirname "$(dirname "$c")")")-$(basename "$c" .pt)"
  tag="${tag//[^A-Za-z0-9]/}"
  echo "=== $tag  <- $c"
  OMR_SCAN_EVAL_WEIGHTS="$c" python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py \
      --rows "$ROW" --tag "$tag" --out "/tmp/screen_${tag}.json" 2>&1 | tail -3
  TAGS+=("$tag")
done

echo
echo "######## class-space survival, one page, vs production ########"
python3 "$SURVEY/probe_confidence_shift.py" --rows "$ROW" \
    --arms prodbase "${TAGS[@]}" --gate prodbase || true
