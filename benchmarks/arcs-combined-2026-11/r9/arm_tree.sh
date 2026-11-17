#!/bin/zsh
# 2.305 r9: re-adjudicate one r9 gather with a given TREE's code, flags ON or OFF. usage: arm_tree.sh TREE GATHER OUTNAME on|off
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/r9
cd $1
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11
if [ $4 = on ]; then F=1; else F=0; fi
echo "$(date +%T) start $3" >> $S/progress.txt
OMR_PAGE_ARC_WRITE=$F OMR_ARC_MEETING_AT_HEAD=$F python3 benchmarks/arcs-combined-2026-11/r9/replay.py $S/$2.record.json $S/$3 --keep-record > $S/$3.log 2>&1
echo "$(date +%T) done $3 rc=$?" >> $S/progress.txt
