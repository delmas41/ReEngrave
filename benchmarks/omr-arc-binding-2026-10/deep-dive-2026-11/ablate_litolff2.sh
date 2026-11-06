#!/bin/zsh
# Litolff second pass (after the first queue): base + the arms that moved anything, again with the mini-record (judged scorer) and refusals.
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b
OUT=scratch/dd
A=benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/arm.py

export OMR_SURYA_KEEP_ALIVE=0
run() { name=$1; shift; echo "== $name $(date +%T)"; python3 $A litolff $name $OUT "$@" 2>&1 | tail -3; python3 benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/slimfile.py $OUT/litolff.$name.arcs.json >/dev/null 2>&1; }
run base
run nobind OMR_ARC_BIND_PAGEWIDE=0
run nounison2 OMR_UNISON_TWO_NOTES=0

echo ALLDONE
