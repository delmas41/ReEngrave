#!/bin/bash
# 2.255 r2 measures: OFF = 20261029-night slices; ON = the same slices with the far-head ledger rows re-read with OMR_LEDGER_READ.
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a37eb51cd656cda0a
export PYTHONPATH=$PWD LANE_REPORT_SAMPLE=$PWD/out/2.255/sample2.json OMR_SURYA_KEEP_ALIVE=0
python3 -m tools.omr.staged.lane_report --flag OMR_LEDGER_READ --from adjudicate --replay-gathered --workers 2 \
  --tag /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night --out out/2.255/lane-off-r2 > out/2.255/lane-off-r2.log 2>&1
python3 -m tools.omr.staged.lane_report --flag OMR_LEDGER_READ --from adjudicate --replay-gathered --workers 2 \
  --tag $PWD/out/2.255/slices-on-r2 --out out/2.255/lane-on-r2 > out/2.255/lane-on-r2.log 2>&1
echo done > out/2.255/lane_done_r2
