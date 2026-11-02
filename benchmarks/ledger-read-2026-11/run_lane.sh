#!/bin/bash
# 2.255 measures: the same tree, ADJUDICATE..EXPORT replayed on the night slices (OFF) and on the slices whose far-head
# ledger rows were re-read with OMR_LEDGER_READ on (ON); both arms with 2.248 r4's OMR_FARHEAD_UNREAD_GUESSED=1 (landing ON).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a52c1f1849a38f236
export LANE_REPORT_SAMPLE=$PWD/out/2.255/sample2.json OMR_FARHEAD_UNREAD_GUESSED=1 OMR_SURYA_KEEP_ALIVE=0
python3 -m tools.omr.staged.lane_report --flag OMR_LEDGER_READ --from adjudicate --replay-gathered --workers 2 \
  --tag /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night --out out/2.255/lane-off > out/2.255/lane-off.log 2>&1
python3 -m tools.omr.staged.lane_report --flag OMR_LEDGER_READ --from adjudicate --replay-gathered --workers 2 \
  --tag $PWD/out/2.255/slices-on --out out/2.255/lane-on > out/2.255/lane-on.log 2>&1
echo done
