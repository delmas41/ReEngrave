#!/bin/sh
# ROADMAP 2.182: after run_whole.sh, re-run ONE arm (the witness window changed after it started); same load cap.
# usage: sh run_after.sh WHOLE_LOG DOC SOURCE OUTDIR ARM
cd "$(dirname "$0")/../../.." || exit 1
until grep -q WHOLE_DONE "$1"; do sleep 60; done
while [ "$(ps -axo rss,comm | awk '$1>10485760 && /[Pp]ython/' | wc -l)" -ge 2 ]; do sleep 60; done
date
python3 benchmarks/omr-two-parts-one-staff-2026-10/probe/m1_replay.py "$2" "$3" "$4" "$5"
echo AFTER_DONE
