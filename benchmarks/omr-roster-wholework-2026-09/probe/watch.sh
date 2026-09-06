#!/bin/bash
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
prev=""
while true; do
  cur=$(ls "$BENCH"/out/ 2>/dev/null | grep 'whole.*\.json$' | sort)
  comm -13 <(echo "$prev") <(echo "$cur")
  prev="$cur"
  n=$(pgrep -f 'tools.omr.transcribe' | wc -l)
  if [ "$n" -le 1 ]; then echo "ALL_RUNS_FINISHED"; exit 0; fi
  sleep 60
done
