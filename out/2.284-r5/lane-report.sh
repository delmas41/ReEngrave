#!/bin/zsh
# 2.284 r5: the lane's measure -- both arms fresh from gather on the r2 dev sample, master cell map, flag OFF vs ON (CLAUDE section 2 rule 4).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a86a05bfc6fca6a28
export OMR_SURYA_KEEP_ALIVE=0
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export LANE_REPORT_SAMPLE=benchmarks/page-ledger-owns-2026-11/sample-r2.json
python3 -u -m tools.omr.staged.lane_report --flag OMR_PAGE_LEDGER_OWNS --from gather --cell-map master --workers 2 \
  --unjudged-tiles 12 --out out/2.284-r5/lane-report > out/2.284-r5/lane-report.log 2>&1
echo DONE > out/2.284-r5/lane-report.done
