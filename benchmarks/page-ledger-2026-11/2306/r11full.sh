#!/bin/zsh
# 2306 r11: ONE full frozen-sample flag-ON gather per plate on the pre-retire tree with the r11 reader (2306-tree-r11, page_stems.py = lane 4537d2cb0),
# then slices, lane reports OFF vs ON, and the replays with EXPORT fates. One heavy job at a time.
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r11full.done
T=$S/2306-tree-r11
export OMR_SURYA_KEEP_ALIVE=0 TREE=$T
echo "start $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r11-lit litolff 1,2,4,6,8,9,10,11,16 OMR_PAGE_STEMS=1
echo "gather lit $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r11-bra brahms 0,4,5,8,12,14,19,25 OMR_PAGE_STEMS=1
echo "gather bra $(date +%T)" >> $D
cd $T
python3 $S/2306-an/to_slices.py $S/2306-gather/2306-r11-lit.record.json $S/2306-slices11 litolff > /dev/null 2>&1
python3 $S/2306-an/to_slices.py $S/2306-gather/2306-r11-bra.record.json $S/2306-slices11 brahms > /dev/null 2>&1
echo "slices $(date +%T)" >> $D
for pl in litolff brahms; do
  python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates $pl --from adjudicate --replay-gathered --tag $S/2306-slices11 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/r6/lr11-$pl > $S/r6/lr11-$pl.txt 2>&1
  echo "lr11 $pl $(date +%T)" >> $D
done
for p in lit bra; do
  python3 $S/r6/replay_fates.py $S/2306-gather/2306-r11-$p.record.json $S/r6/rf11-$p > $S/r6/rf11-$p.txt 2>&1
  echo "rf11 $p $(date +%T)" >> $D
done
echo ALL >> $D
