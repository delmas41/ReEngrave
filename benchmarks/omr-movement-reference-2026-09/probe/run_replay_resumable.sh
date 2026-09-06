#!/bin/bash
# Drive replay_slots.py until its page cache is complete, restarting it whenever
# the read phase wedges (see read()'s docstring — it stalls at the ~22nd margin
# read on a long run and the cause is not yet known). Each attempt is killed
# after $STALL seconds without the cache growing, and the next one resumes from
# what is already cached.
#
#   $1 tag   $2 --pages   [$3 attempts]
set -u
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OUT=benchmarks/omr-movement-reference-2026-09/out
CACHE="$OUT/cache-$1"
LOG="$OUT/replay-$1.txt"
ATTEMPTS="${3:-40}"
STALL=90
mkdir -p "$CACHE"

for attempt in $(seq 1 "$ATTEMPTS"); do
  OMR_SURYA_KEEP_ALIVE=0 python3 -u \
      benchmarks/omr-movement-reference-2026-09/probe/replay_slots.py "$PDF" \
      --pages "$2" --cache "$CACHE" --out "$OUT/replay-$1.json" \
      > "$LOG" 2>&1 &
  pid=$!
  last=$(ls "$CACHE" | wc -l); idle=0
  while kill -0 $pid 2>/dev/null; do
    sleep 10
    now=$(ls "$CACHE" | wc -l)
    if [ "$now" -gt "$last" ]; then last=$now; idle=0; else idle=$((idle + 10)); fi
    if [ "$idle" -ge "$STALL" ]; then
      echo "attempt $attempt: stalled at $now cached pages, restarting" \
          >> "$OUT/replay-$1.attempts.txt"
      kill -9 $pid 2>/dev/null
      # ⚠️ DO NOT pkill llama-server HERE. It is the SHARED persistent Surya
      # server (`staff_labels_surya --serve`), and other agents on this machine
      # are reading margins through it — killing it to tidy up after our own
      # wedge would break their runs, and it was in this script for one
      # revision before that was noticed.
      break
    fi
  done
  wait $pid 2>/dev/null
  if grep -q "^IMPOSSIBLE by arm" "$LOG" 2>/dev/null; then
    echo "attempt $attempt: COMPLETE ($(ls "$CACHE" | wc -l) pages cached)" \
        >> "$OUT/replay-$1.attempts.txt"
    exit 0
  fi
done
echo "gave up after $ATTEMPTS attempts" >> "$OUT/replay-$1.attempts.txt"
exit 1
