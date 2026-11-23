#!/bin/zsh
# 2306 r4: re-gather (the extent is GATHER) on the frozen pre-retire tree + twin fix + r4 extent; then slices, lane reports, diag replays
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
export TREE=$S/2306-tree-preretire
D=$S/2306-r4.done
zsh $S/2306-gather/run_one.sh smp4-lit litolff 1,2,4,6,8,9,10,11,16 OMR_PAGE_STEMS=1
echo "gather lit $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh smp4-bra brahms 0,4,5,8,12,14,19,25 OMR_PAGE_STEMS=1
echo "gather bra $(date +%T)" >> $D
cd $TREE
python3 $S/2306-an/to_slices.py $S/2306-gather/2306-smp4-lit.record.json $S/2306-slices4 litolff
python3 $S/2306-an/to_slices.py $S/2306-gather/2306-smp4-bra.record.json $S/2306-slices4 brahms
for pl in litolff brahms; do
  python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates $pl --from adjudicate --replay-gathered --tag $S/2306-slices4 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/2306-lr4-$pl > $S/2306-lr4-$pl.txt 2>&1
  echo "lr4 $pl $(date +%T)" >> $D
done
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp4-lit.record.json $S/2306-diag4-lit > $S/2306-diag4-lit.txt 2>&1
echo "diag4 lit $(date +%T)" >> $D
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp4-bra.record.json $S/2306-diag4-bra > $S/2306-diag4-bra.txt 2>&1
echo "diag4 bra $(date +%T)" >> $D
echo ALL >> $D
