#!/bin/bash
# 2.252 r5: re-adjudicate a saved gather on THIS tree with one arm's flags. args: IN OUT ARM(off|on)
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf
export OMR_UNISON_TIE_VOICE=1 OMR_SURYA_KEEP_ALIVE=0
if [ "$3" = on ]; then
  export OMR_HEAD_HOLE_POSITION=1 OMR_TIE_CARRIES_ACCIDENTAL=1 OMR_ARC_TRACE_NOT_A_LINE=1
else
  export OMR_HEAD_HOLE_POSITION=0 OMR_TIE_CARRIES_ACCIDENTAL=0 OMR_ARC_TRACE_NOT_A_LINE=0
fi
python3 benchmarks/hairpin-reach-2026-11/readjudicate.py "$1" "$2" > "$2.log" 2>&1
echo "$2 rc=$? $(date)" >> out/2.252r5/readj.done
