#!/bin/zsh
# 2306 r8 measurement: after the r8 gathers + lane reports (r7/r8.sh) finish, replay the r8 gathers:
#   rf8   = pre-retire tip (2306-tree-r7), both arms, with EXPORT fates  -> cause count, tile places
#   ng8   = same tree with the r7 no-stem guard off, ON arm only          -> what the guard moves
#   rt8   = the branch tip WITH the retire commit (2306-tree-r8-retire), ON arm only, and its lane reports
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r8m.done
export OMR_SURYA_KEEP_ALIVE=0
until grep -q "^ALL" $S/r7/r8.done 2>/dev/null; do sleep 30; done
echo "start $(date +%T)" >> $D
for p in lit bra; do
  R=$S/2306-gather/2306-r8-$p.record.json
  cd $S/2306-tree-r7 && python3 $S/r6/replay_fates.py $R $S/r6/rf8-$p > $S/r6/rf8-$p.txt 2>&1; echo "rf8 $p $(date +%T)" >> $D
  cd $S/2306-tree-r8-noguard && python3 $S/r6/replay_fates.py $R $S/r6/ng8-$p --arms on > $S/r6/ng8-$p.txt 2>&1; echo "ng8 $p $(date +%T)" >> $D
  cd $S/2306-tree-r8-retire && python3 $S/r6/replay_fates.py $R $S/r6/rt8-$p --arms on > $S/r6/rt8-$p.txt 2>&1; echo "rt8 $p $(date +%T)" >> $D
done
cd $S/2306-tree-r8-retire
for pl in litolff brahms; do
  python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates $pl --from adjudicate --replay-gathered --tag $S/2306-slices8 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/r6/lrrt8-$pl > $S/r6/lrrt8-$pl.txt 2>&1
  echo "lrrt8 $pl $(date +%T)" >> $D
done
echo ALL >> $D
