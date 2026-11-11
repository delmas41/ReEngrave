#!/bin/bash
# 2.291: serial replays (one gather-sized job at a time). usage: run_all.sh OUTROOT
set -e
cd "$(dirname "$0")/../.."
O="$1"
python3 benchmarks/one-chord-one-event-2026-11/capture.py brahms 0,4 "$O/def" > "$O/def_brahms.log" 2>&1
python3 benchmarks/one-chord-one-event-2026-11/capture.py litolff 1,2,4,6,8,9,10,11,16 "$O/wide" > "$O/wide_litolff.log" 2>&1
python3 benchmarks/one-chord-one-event-2026-11/capture.py brahms 0,4,5,8,12,14,19,25 "$O/wide" > "$O/wide_brahms.log" 2>&1
echo done > "$O/run_all.done"
