#!/bin/zsh
# Brahms p0+p5 second pass: every arm again with the mini-record (judged scorer) and refusals; adds OMR_PAGE_CLAIMS=0 (adjudicate side only).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-ab22b9e5e1af96e0b
OUT=scratch/dd
A=benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/arm.py
export OMR_SURYA_KEEP_ALIVE=0
run() { name=$1; shift; echo "== $name $(date +%T)"; python3 $A brahms $name $OUT --only-pages 0,5 --pages 0,5 "$@" 2>&1 | tail -3; python3 benchmarks/omr-arc-binding-2026-10/deep-dive-2026-11/slimfile.py $OUT/brahms.$name.arcs.json >/dev/null 2>&1; }
run nobind OMR_ARC_BIND_PAGEWIDE=0
run nopageclaims OMR_PAGE_CLAIMS=0
run noendpitch OMR_BIND_END_PITCH=0
run nonotline OMR_ARC_TRACE_NOT_A_LINE=0
run nopairside OMR_TIE_PAIR_ARC_SIDE=0
run noacc OMR_TIE_CARRIES_ACCIDENTAL=0
run unisonvoice OMR_UNISON_TIE_VOICE=1
run kindends OMR_ARC_KIND_FROM_ENDS=1
run anchors OMR_SLUR_FROM_ANCHORS=1
run notail OMR_ARC_TAIL_NOT_A_HEAD=0
run nounison2 OMR_UNISON_TWO_NOTES=0
echo ALLDONE
