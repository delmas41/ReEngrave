#!/bin/zsh
# 2306 r12 step 1: the SAME pages (Litolff 2, 4, 9: the r11 losses) gathered with the r9 reader and the r11 reader, then both replayed ON (and r11 OFF),
# so r9 -> r11 is the reader's change alone, not two gathers' own variation. One gather at a time.
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r12g.done
export OMR_SURYA_KEEP_ALIVE=0
echo "start $(date +%T)" >> $D
TREE=$S/2306-tree-r7 zsh $S/2306-gather/run_one.sh r9-lit3 litolff 2,4,9 OMR_PAGE_STEMS=1
echo "r9 gather $(date +%T)" >> $D
TREE=$S/2306-tree-r11 zsh $S/2306-gather/run_one.sh r11-lit3 litolff 2,4,9 OMR_PAGE_STEMS=1
echo "r11 gather $(date +%T)" >> $D
cd $S/2306-tree-r7 && python3 $S/r6/replay_fates.py $S/2306-gather/2306-r9-lit3.record.json $S/r6/rf9-lit3 --arms on > $S/r6/rf9-lit3.txt 2>&1
cd $S/2306-tree-r11 && python3 $S/r6/replay_fates.py $S/2306-gather/2306-r11-lit3.record.json $S/r6/rf11-lit3 > $S/r6/rf11-lit3.txt 2>&1
echo ALL >> $D
