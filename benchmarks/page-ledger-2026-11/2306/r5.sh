#!/bin/zsh
# 2306 r5: pre-retire frozen tree + the direction hand-off fix; replays of the r4 gathers only
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/2306-r5.done
cd $S/2306-tree-preretire
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp4-lit.record.json $S/2306-diag5-lit > $S/2306-diag5-lit.txt 2>&1
echo "diag5 lit $(date +%T)" >> $D
for pl in litolff brahms; do
  python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates $pl --from adjudicate --replay-gathered --tag $S/2306-slices4 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/2306-lr5-$pl > $S/2306-lr5-$pl.txt 2>&1
  echo "lr5 $pl $(date +%T)" >> $D
done
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp4-bra.record.json $S/2306-diag5-bra > $S/2306-diag5-bra.txt 2>&1
echo "diag5 bra $(date +%T)" >> $D
echo ALL >> $D
