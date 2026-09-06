#!/bin/bash
BENCH="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$BENCH"/out/*.log; do
  echo "--- $(basename "$f" .log)"
  tail -2 "$f"
done
echo "--- live"
pgrep -fl 'tools.omr.transcribe' | grep -c Python
