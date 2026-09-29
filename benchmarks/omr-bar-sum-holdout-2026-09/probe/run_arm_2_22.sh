#!/bin/sh
# ROADMAP 2.22 pricing. Usage:
#   sh run_arm_2_22.sh <tree root> <label> <record> [--redecide-only]
# Runs held_funnel_mvt_2_22.py FROM <tree root> (this worktree = arm, a
# `git archive HEAD` copy = base) so base and arm differ only in the code.
TREE="$1"; LABEL="$2"; REC="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
R="$HERE/../out/r222"
mkdir -p "$R"
export OMR_SURYA_KEEP_ALIVE=0
cd "$TREE" || exit 1
nohup python3 "$TREE/benchmarks/omr-bar-sum-holdout-2026-09/probe/held_funnel_mvt_2_22.py" \
  "$REC" --label "$LABEL" --out-dir "$R" --redecide --skip-own --musicxml \
  > "$R/$LABEL.log" 2>&1 &
echo "started $LABEL from $TREE"
