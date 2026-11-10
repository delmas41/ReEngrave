#!/bin/bash
# 2.282: re-adjudicate one plate under one OMR_CLAIM_ORDER arm. usage: run_arm.sh MODE PLATE   (MODE heads_first|accidentals_first)
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a2667cb15d74f1e2f
export OMR_SURYA_KEEP_ALIVE=0
export OMR_CLAIM_ORDER=$1
OUT=out/2.282/$1
mkdir -p "$OUT"
python3 probe/2.282/readj.py $2 "$OUT/$2" > "$OUT/readj_$2.log" 2>&1
echo done > "$OUT/$2.done"
