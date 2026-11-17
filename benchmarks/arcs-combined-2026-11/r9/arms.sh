#!/bin/zsh
# 2.305 r9: re-adjudicate the one r9 gather (g0) on THIS tree for each arm, then the judge count. usage: TAG=before arms.sh [off] [on]
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a74f60b633a6bef05
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/r9
cd $W
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11
for arm in "$@"; do
  if [ $arm = on ]; then F=1; else F=0; fi
  O=$S/${TAG}-$arm
  echo "$(date +%T) start $TAG-$arm $(git rev-parse --short HEAD)" >> $S/progress.txt
  OMR_PAGE_ARC_WRITE=$F OMR_ARC_MEETING_AT_HEAD=$F python3 benchmarks/arcs-combined-2026-11/r9/replay.py $S/${GATHER:-g0}.record.json $O --keep-record > $O.log 2>&1
  python3 benchmarks/note-loss-funnel-2026-11/judge.py $O.facts.json --json $O.judge.json > $O.judge.txt 2>&1
  python3 benchmarks/arcs-combined-2026-11/r9/tally.py $O --json $O.tally.json > $O.tally.txt 2>&1
  echo "$(date +%T) done $TAG-$arm" >> $S/progress.txt
done
