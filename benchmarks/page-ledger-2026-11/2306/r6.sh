#!/bin/zsh
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
D=$S/r6/r6.done
export OMR_SURYA_KEEP_ALIVE=0
cd $S/2306-tree-preretire
# the stopped agent's diag_fates (Litolff, both arms) is still running: one heavy job at a time
for i in $(seq 1 120); do grep -q "^on fates" $S/2306-fates-lit.txt && break; sleep 30; done
echo "start $(date +%T)" >> $D
python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates litolff --from adjudicate --replay-gathered --tag $S/2306-slices4 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/r6/lrctl-litolff > $S/r6/lrctl-litolff.txt 2>&1
echo "lrctl litolff $(date +%T)" >> $D
python3 $S/r6/replay_fates.py $S/2306-gather/2306-smp4-lit.record.json $S/r6/rf-lit > $S/r6/rf-lit.txt 2>&1
echo "rf lit $(date +%T)" >> $D
python3 $S/r6/replay_fates.py $S/2306-gather/2306-smp4-bra.record.json $S/r6/rf-bra > $S/r6/rf-bra.txt 2>&1
echo "rf bra $(date +%T)" >> $D
python3 -m tools.omr.staged.lane_report --flag OMR_PAGE_STEMS --plates brahms --from adjudicate --replay-gathered --tag $S/2306-slices4 --workers 2 --seed 2306 --unjudged-tiles 0 --out $S/r6/lrctl-brahms > $S/r6/lrctl-brahms.txt 2>&1
echo "lrctl brahms $(date +%T)" >> $D
echo ALL >> $D
