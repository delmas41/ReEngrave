#!/bin/bash
# One page-set arm, run twice (flag off / on) so the pair can be compared.
# $1 = tag   $2 = pdf   $3 = --pages argument
set -u
OUT=benchmarks/omr-movement-reference-2026-09/out
for FLAG in 0 1; do
  OMR_MOVEMENT_REFERENCE=$FLAG python3 -m tools.omr.transcribe "$2" \
      --pages "$3" --no-direction-text \
      --out "$OUT/$1-flag$FLAG.json" > "$OUT/$1-flag$FLAG.log" 2>&1
  echo "exit=$? tag=$1 flag=$FLAG" >> "$OUT/$1-flag$FLAG.log"
done
