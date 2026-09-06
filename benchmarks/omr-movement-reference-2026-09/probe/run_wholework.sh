#!/bin/bash
# One whole-work arm. $1 = tag, $2 = OMR_MOVEMENT_REFERENCE value.
set -u
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OUT=benchmarks/omr-movement-reference-2026-09/out
export OMR_MOVEMENT_REFERENCE="$2"
python3 -m tools.omr.transcribe "$PDF" --pages 0-87 --no-direction-text \
    --out "$OUT/beet5-whole-$1.json" > "$OUT/beet5-whole-$1.log" 2>&1
echo "exit=$? tag=$1 flag=$2" >> "$OUT/beet5-whole-$1.log"
