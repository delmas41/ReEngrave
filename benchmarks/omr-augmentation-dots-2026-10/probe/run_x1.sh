#!/bin/sh
# 2.180: run the dot-fate extract on both 20261018-night records, one at a time (Litolff, then Brahms).
# usage: sh run_x1.sh OUTDIR   (run from the worktree root)
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
python3 benchmarks/omr-augmentation-dots-2026-10/probe/x1_extract.py $L/beethoven5-litolff-mvt1-whole-20261018-night.record.json "$1/lit_x1.json"
python3 benchmarks/omr-augmentation-dots-2026-10/probe/x1_extract.py $L/brahms1-breitkopf-mvt1-whole-20261018-night.record.json "$1/bra_x1.json"
