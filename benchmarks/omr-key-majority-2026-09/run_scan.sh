#!/bin/sh
# One document, three runs: the control, the base arm and the test arm.
set -e
REC="$1"; TAG="$2"
OUT=benchmarks/omr-key-majority-2026-09/out
R=benchmarks/omr-key-majority-2026-09/readjudicate.py
python3 "$R" "$REC" --control
python3 "$R" "$REC" --off all --out "$OUT/$TAG-base.json"
python3 "$R" "$REC"            --out "$OUT/$TAG-arm.json"
python3 -m tools.omr.staged.export "$OUT/$TAG-base.json" --out "$OUT/$TAG-base.musicxml"
python3 -m tools.omr.staged.export "$OUT/$TAG-arm.json"  --out "$OUT/$TAG-arm.musicxml"
