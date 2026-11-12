#!/bin/bash
# ROADMAP 2.290 build: re-run ONLY the ADJUDICATE..EXPORT arms of a lane report on its own saved gathers (an ADJUDICATE-only change; the GATHER code
# that made the gathers is unchanged), then re-read the arms (--reuse) for the report. Same flags, same pages, same tree for both arms.
# usage: rearm.sh OUTDIR   (OUTDIR = a `run_measure.sh` output with work/<plate>.<arm>.gathered.record.json)
cd "$(dirname "$0")/../.."
W=$(pwd)
OUT=$1
export OMR_SURYA_KEEP_ALIVE=0 LANE_REPORT_SAMPLE=$W/benchmarks/page-heads-ledger-2026-11/sample-2290.json
FL="--flag OMR_PAGE_HEAD_ONE=0:1 --flag OMR_PAGE_HEAD_LEDGER=0:1"
for spec in "litolff 2,8,11" "brahms 14,19"; do
  set -- $spec
  for arm in off on; do
    while [ "$(ps aux | grep -E 'tools\.omr\.staged' | grep -v grep | wc -l | tr -d ' ')" -ge 2 ]; do sleep 20; done
    python3 -u -m tools.omr.staged.lane_report arm --tag 20261029-night --work "$OUT/work" --from gather $FL --plate $1 --arm $arm --pages $2 \
      --gathered "$OUT/work/$1.$arm.gathered.record.json" > "$OUT/work/$1.$arm.log" 2>&1 || echo "arm $1 $arm failed"
  done
done
python3 -u -m tools.omr.staged.lane_report --flag OMR_PAGE_HEAD_ONE --flag OMR_PAGE_HEAD_LEDGER --from gather --cell-map master --reuse --out "$OUT" > "$OUT.rearm.log" 2>&1
echo "done rc=$?" >> "$OUT.rearm.log"
