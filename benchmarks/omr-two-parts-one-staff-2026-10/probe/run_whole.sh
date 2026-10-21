#!/bin/sh
# ROADMAP 2.182 whole-movement replay (20261018-night slices, cut by 2.177's slice_record.py), one arm at a time;
# waits while two or more pythons over 10 GB run (Sean's load cap, DECISIONS 2026-10-12 "HOW LANES RUN").
# usage: sh run_whole.sh SLICEROOT OUTDIR
cd "$(dirname "$0")/../../.." || exit 1
P=benchmarks/omr-two-parts-one-staff-2026-10/probe/m1_replay.py
waitcap() {
  while [ "$(ps -axo rss,comm | awk '$1>10485760 && /[Pp]ython/' | wc -l)" -ge 2 ]; do sleep 60; done
  date
}
for doc in litolff brahms; do
  for arm in off on; do
    waitcap
    python3 $P $doc "$1/$doc" "$2" $arm
  done
done
echo WHOLE_DONE
