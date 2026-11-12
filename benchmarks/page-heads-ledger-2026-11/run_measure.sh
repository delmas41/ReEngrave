#!/bin/bash
# ROADMAP 2.290 build: the lane report, flags OFF vs ON (OMR_PAGE_HEAD_ONE + OMR_PAGE_HEAD_LEDGER), fresh page gathers both arms, master cell map, on
# sample-2290.json (Litolff p2, p8, p11; Brahms p14, p19), one process at a time; the ON gathers also cut the real-case crops (dump-all.json).
# Waits until fewer than two `tools.omr.staged` processes run (CLAUDE: at most two gathers on the machine).
cd "$(dirname "$0")/../.."
W=$(pwd)
OUT=${1:-out/lane-report/2.290-build}
while [ "$(ps aux | grep -E 'tools\.omr\.staged' | grep -v grep | wc -l | tr -d ' ')" -ge 2 ]; do sleep 30; done
export OMR_SURYA_KEEP_ALIVE=0 LANE_REPORT_SAMPLE=$W/benchmarks/page-heads-ledger-2026-11/sample-2290.json
export OMR_PAGE_HEAD_CASES_DUMP=$W/benchmarks/page-heads-ledger-2026-11/real_cases/dump-all.json
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
python3 -u -m tools.omr.staged.lane_report --flag OMR_PAGE_HEAD_ONE --flag OMR_PAGE_HEAD_LEDGER --from gather --cell-map master --workers 1 --out "$OUT" > "$OUT.log" 2>&1
echo "done rc=$?" >> "$OUT.log"
