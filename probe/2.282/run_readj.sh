#!/bin/bash
# 2.282: re-adjudicate the saved 20261104-night slices on the current tree (flags as the env says); never re-gather.
# usage: run_readj.sh OUTROOT   (e.g. out/2.282/base); extra env (OMR_CLAIM_ORDER=...) passes through
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a2667cb15d74f1e2f
export OMR_SURYA_KEEP_ALIVE=0
OUT=${1:-out/2.282/base}
mkdir -p "$OUT"
for p in litolff brahms; do
  python3 probe/2.282/readj.py $p "$OUT/$p" > "$OUT/readj_$p.log" 2>&1
done
echo ALLDONE > "$OUT/readj.done"
