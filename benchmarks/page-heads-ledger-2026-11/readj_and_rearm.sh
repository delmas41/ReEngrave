#!/bin/bash
# ROADMAP 2.290 build: re-adjudicate both arms' saved gathers on THIS tree (OFF env for off, ON env for on), then export + report them (rearm.sh).
# usage: readj_and_rearm.sh SRC_OUTDIR DST_OUTDIR
cd "$(dirname "$0")/../.."
SRC=$1; DST=$2
mkdir -p "$DST/work"
for p in litolff brahms; do
  for arm in off on; do
    V=0; [ $arm = on ] && V=1
    PYTHONPATH=. OMR_PAGE_HEAD_ONE=$V OMR_PAGE_HEAD_LEDGER=$V python3 benchmarks/page-heads-ledger-2026-11/readjudicate.py \
      "$SRC/work/$p.$arm.gathered.record.json" "$DST/work/$p.$arm.gathered.record.json" >> "$DST.readj.log" 2>&1
  done
done
benchmarks/page-heads-ledger-2026-11/rearm.sh "$DST"
