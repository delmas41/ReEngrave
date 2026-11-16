#!/bin/zsh
# 2306 r11 baseline: the same two-page gathers with the r9 reader (2306-tree-r7), so r9 -> r11 compares like with like
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r9g2.done
export OMR_SURYA_KEEP_ALIVE=0 TREE=$S/2306-tree-r7
until grep -q "^ALL" $S/r6/r11g.done; do sleep 15; done
echo "start $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r9-lit2 litolff 6,10 OMR_PAGE_STEMS=1
echo "lit2 $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r9-bra2 brahms 12,14 OMR_PAGE_STEMS=1
echo "bra2 $(date +%T)" >> $D
cd $S/2306-tree-r7
python3 $S/r6/replay_fates.py $S/2306-gather/2306-r9-lit2.record.json $S/r6/rf9-lit2 --arms on > $S/r6/rf9-lit2.txt 2>&1
python3 $S/r6/replay_fates.py $S/2306-gather/2306-r9-bra2.record.json $S/r6/rf9-bra2 --arms on > $S/r6/rf9-bra2.txt 2>&1
cd $S/2306-tree-r11
python3 $S/r6/replay_fates.py $S/2306-gather/2306-r11-bra2.record.json $S/r6/rf11-bra2 > $S/r6/rf11-bra2.txt 2>&1
echo ALL >> $D
