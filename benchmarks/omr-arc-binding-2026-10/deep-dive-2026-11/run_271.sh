#!/bin/zsh
# Sean's 2.271 closest-note tiles 2,4,5,9,10,12: re-adjudicate the saved gather with the lane's own code (r1 = 8d6f7fdbb, the one the tiles were cut from;
# exported read-only with `git archive` to scratch/t271r1) with OMR_ARC_CLOSEST_HEAD=1, and again with the 2.271 head (69b87361b, scratch/t271).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b
OUT=scratch/dd
A=benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/arm.py
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b
export OMR_SURYA_KEEP_ALIVE=0
echo "== brahms r1 $(date +%T)"; python3 $A brahms r1closest $OUT --code $W/scratch/t271r1 --only-pages 0,14 --pages 0,14 OMR_ARC_CLOSEST_HEAD=1 2>&1 | tail -2
echo "== brahms r1 control (flag off, same code) $(date +%T)"; python3 $A brahms r1off $OUT --code $W/scratch/t271r1 --only-pages 0,14 --pages 0,14 2>&1 | tail -2
echo "== litolff r1 $(date +%T)"; python3 $A litolff r1closest $OUT --code $W/scratch/t271r1 --only-pages 1,4,10,11 --pages 4,10,11 OMR_ARC_CLOSEST_HEAD=1 2>&1 | tail -2
echo "== litolff r1 control $(date +%T)"; python3 $A litolff r1off $OUT --code $W/scratch/t271r1 --only-pages 1,4,10,11 --pages 4,10,11 2>&1 | tail -2
for f in brahms.r1closest brahms.r1off litolff.r1closest litolff.r1off; do python3 benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/slimfile.py $OUT/$f.arcs.json; done
echo ALLDONE
