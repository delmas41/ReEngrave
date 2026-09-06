#!/bin/bash
# Replay the slot assignment over a page LIST, both arms, one detection pass.
# $1 = tag, $2 = --pages argument.
#
# OMR_SURYA_KEEP_ALIVE=0 on purpose: the resident margin server is shared with
# whatever else is running on this machine, and queueing behind another
# document's 88 pages stalls this at 0% CPU indefinitely. Spawning our own
# reader is slower per page and finishes.
set -u
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OUT=benchmarks/omr-movement-reference-2026-09/out
OMR_SURYA_KEEP_ALIVE=0 python3 -u \
    benchmarks/omr-movement-reference-2026-09/probe/replay_slots.py "$PDF" \
    --pages "$2" --out "$OUT/replay-$1.json" > "$OUT/replay-$1.txt" 2>&1
echo "exit=$?" >> "$OUT/replay-$1.txt"
