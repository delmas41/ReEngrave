#!/bin/zsh
# One page at a time (the detector is heavy): Litolff sample pages, then Brahms p0 and p5. Work files go to out/trial-work/ (not committed).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-aca2654680d85413f || exit 1
export OMR_SURYA_KEEP_ALIVE=0
H=benchmarks/omr-arc-binding-2026-10/barline-crop-trial-2026-11
W=out/trial-work/run
mkdir -p $W
for p in 2 4 6 8 9 10 11 16; do
  python3 $H/run_page.py litolff $p $W/litolff.p$p.json --arms A,B,B2,C $([ $p = 2 ] && echo --control-bad) 2>&1 | grep -v -i warn
done
for p in 0 5; do
  python3 $H/run_page.py brahms $p $W/brahms.p$p.json --arms A,B,B2,C $([ $p = 0 ] && echo --control-bad) 2>&1 | grep -v -i warn
done
echo ALLDONE
