#!/bin/zsh
# 2306 r11: two-page flag-ON gathers of the control pages on the frozen pre-retire tree with the r11 reader (2306-tree-r11), one at a time
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r11g.done
export OMR_SURYA_KEEP_ALIVE=0 TREE=$S/2306-tree-r11
echo "start $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r11-lit2 litolff 6,10 OMR_PAGE_STEMS=1
echo "lit2 $(date +%T)" >> $D
zsh $S/2306-gather/run_one.sh r11-bra2 brahms 12,14 OMR_PAGE_STEMS=1
echo "bra2 $(date +%T)" >> $D
echo ALL >> $D
