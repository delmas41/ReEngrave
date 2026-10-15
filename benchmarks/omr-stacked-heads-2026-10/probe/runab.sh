#!/bin/bash
# usage: runab.sh  (cwd = the 2.129 tree). One gather at a time, nice. Records + musicxml to scratch.
R=/Users/seanjohnson/Desktop/ReEngrave
SP=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-roadmap-start-d5bd81/2613ea77-41a2-444d-8442-c16de9f48d6f/scratchpad/2.129/runs
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81
waitfree() { while pgrep -f "tools.omr.staged|chain1.sh|acceptance_quick" >/dev/null; do sleep 15; done; sleep 20; pgrep -f "tools.omr.staged|chain1.sh|acceptance_quick" >/dev/null && waitfree; }
BRA=library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
LIT=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
for spec in "bra 0-1 $BRA" "lit 0-3 $LIT"; do
  set -- $spec; tag=$1; pg=$2; pdf=$3
  for arm in off on; do
    waitfree
    v=0; [ $arm = on ] && v=1
    echo "=== $tag $arm $(date +%H:%M:%S) HEAD $(git rev-parse --short HEAD)" >> $SP/progress.log
    OMR_STACKED_SECOND_HEAD=$v PYTHONDONTWRITEBYTECODE=1 nice -n 10 python3 -m tools.omr.staged $pdf --pages $pg --weights auto --no-surya --no-ocr --out $SP/$tag-$arm.json --musicxml $SP/$tag-$arm.musicxml > $SP/$tag-$arm.log 2>&1
    echo "done $tag $arm exit $? $(date +%H:%M:%S)" >> $SP/progress.log
  done
done
echo ALLDONE >> $SP/progress.log
