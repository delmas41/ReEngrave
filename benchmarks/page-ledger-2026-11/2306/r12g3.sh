#!/bin/zsh
# 2306 r12: the r12 reader on the same small page sets as the r9 / r11 small gathers (Litolff 2,4,9 and 6,10), then replays ON (and OFF for lit3)
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r12g3.done
export OMR_SURYA_KEEP_ALIVE=0 TREE=$S/2306-tree-r12
echo "start $(date +%T)" >> $D
until ! ps -axo args | grep -v grep | grep -q -- "-m tools.omr.staged /"; do sleep 30; done
zsh $S/2306-gather/run_one.sh r12b-lit3 litolff 2,4,9 OMR_PAGE_STEMS=1
echo "lit3 $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r12b-lit2 litolff 6,10 OMR_PAGE_STEMS=1
echo "lit2 $(date +%T)" >> $D
cd $S/2306-tree-r12
python3 $S/r6/replay_fates.py $S/2306-gather/2306-r12b-lit3.record.json $S/r6/rf12b-lit3 > $S/r6/rf12b-lit3.txt 2>&1
python3 $S/r6/replay_fates.py $S/2306-gather/2306-r12b-lit2.record.json $S/r6/rf12b-lit2 --arms on > $S/r6/rf12b-lit2.txt 2>&1
echo ALL >> $D
