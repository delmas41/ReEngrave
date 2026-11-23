#!/bin/zsh
# 2306 r9 measurement, replays of the saved r9 gathers only (no new gather), pre-retire tree 2306-tree-r7 (= lane 1dc2b5115 minus the retire commit)
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r9m.done
export OMR_SURYA_KEEP_ALIVE=0
cd $S/2306-tree-r7
echo "start $(date +%T)" >> $D
for pl in litolff brahms; do
  python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates $pl --from adjudicate --replay-gathered --tag $S/2306-slices9 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/r6/lr9-$pl > $S/r6/lr9-$pl.txt 2>&1
  echo "lr9 $pl $(date +%T)" >> $D
done
for p in lit bra; do
  python3 $S/r6/replay_fates.py $S/2306-gather/2306-r9-$p.record.json $S/r6/rf9-$p > $S/r6/rf9-$p.txt 2>&1
  echo "rf9 $p $(date +%T)" >> $D
done
echo ALL >> $D
