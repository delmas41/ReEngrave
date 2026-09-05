#!/bin/zsh
# Dump musicdiff ops for the recorded-run fixtures (sad-austin worktree) into
# ops-baseline/. Usage: run_dump_ops.sh <fixtures-dir> <out-dir>
set -e
FIX=${1:?fixtures dir}
OUT=${2:?out dir}
mkdir -p "$OUT"
for w in beethoven-sym3-mvt1 beethoven-sym5-mvt1 brahms-sym1-mvt1 \
         brahms-sym4-mvt1 bruckner-sym5-mvt1 dvorak-sym9-mvt4 \
         mahler-sym5-mvt1 mozart-sym40-mvt1 mozart-sym41-mvt1 \
         tchaikovsky-sym4-mvt2 tchaikovsky-sym6-mvt2; do
  /Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python \
    /Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-ned-2026-08/dump_ops.py \
    "$FIX/$w.omr.musicxml" "$FIX/$w.musicxml" \
    --json "$OUT/$w.json" > "$OUT/$w.txt" 2>&1 || echo "FAILED $w"
done
echo ALL_DONE
