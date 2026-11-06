#!/bin/bash
# 2.274 step 1: the measurement over a list of PLATE:PAGE pairs, one process at a time.   run_all.sh WORKDIR brahms:5 litolff:4 ...
export OMR_SURYA_KEEP_ALIVE=0
here="$(cd "$(dirname "$0")" && pwd)"
wd="$1"; shift
for pp in "$@"; do
  python3 "$here/measure.py" "${pp%%:*}" "${pp##*:}" "$wd" | cut -c1-24
done
python3 "$here/tally.py" "$wd" | tail -1
