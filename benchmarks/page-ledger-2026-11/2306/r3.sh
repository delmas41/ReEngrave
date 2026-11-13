#!/bin/zsh
# 2306 r3: pre-retire tree + twin fix; lane reports and diag replays, both plates
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
cd $S/2306-tree-preretire
python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates litolff --from adjudicate --replay-gathered --tag $S/2306-slices --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/2306-lr3-lit > $S/2306-lr3-lit.txt 2>&1
echo "lr3-lit $(date +%T)" >> $S/2306-r3.done
python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates brahms --from adjudicate --replay-gathered --tag $S/2306-slices --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/2306-lr3-bra > $S/2306-lr3-bra.txt 2>&1
echo "lr3-bra $(date +%T)" >> $S/2306-r3.done
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp-lit.record.json $S/2306-diag3-lit > $S/2306-diag3-lit.txt 2>&1
echo "diag3-lit $(date +%T)" >> $S/2306-r3.done
python3 $S/2306-an/diag_replay.py $S/2306-gather/2306-smp-bra.record.json $S/2306-diag3-bra > $S/2306-diag3-bra.txt 2>&1
echo "diag3-bra $(date +%T)" >> $S/2306-r3.done
echo ALL >> $S/2306-r3.done
