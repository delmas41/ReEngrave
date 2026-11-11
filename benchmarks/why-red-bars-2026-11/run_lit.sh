#!/bin/bash
# 2.291: Litolff re-capture with stem directions in the glyph rows (default pages, then wide). usage: run_lit.sh OUTROOT
cd "$(dirname "$0")/../.."
O="$1"
python3 benchmarks/why-red-bars-2026-11/capture.py litolff 1,2 "$O/def" > "$O/def_litolff2.log" 2>&1
python3 benchmarks/why-red-bars-2026-11/capture.py litolff 1,2,4,6,8,9,10,11,16 "$O/wide" > "$O/wide_litolff2.log" 2>&1
echo done > "$O/run_lit.done"
