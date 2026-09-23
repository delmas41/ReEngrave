#!/bin/bash
# ROADMAP 2.11 — re-run the ARM side only, against an existing base record.
#
# ⚠️ VALID ONLY BECAUSE THE BASE ARM IS THE COMMIT'S PARENT AND HAS NOT MOVED.
# `run_ab.sh` produced `base-<tag>.record.json` from `<sha>:` versions of the
# three changed files; nothing since has touched those versions, so re-running
# the arm alone is the same experiment, not a cached one. Give every arm its
# own `--out` (CLAUDE.md §6b) — this overwrites `arm-<tag>` on purpose, and
# the wall time is the tell that it really ran.
#
# ⚠️ DO NOT RUN THIS CONCURRENTLY WITH EDITING `tools/`. `run_ab.sh` restores
# files from a scratch copy at its midpoint, and an edit landing in that
# window is silently reverted. Learned the hard way in this lane.
#
#   bash benchmarks/omr-clef-geometry-2026-09/probe/run_arm.sh <pdf> <page> <tag>
set -euo pipefail

PDF="$1"; PAGE="$2"; TAG="$3"
OUT=benchmarks/omr-clef-geometry-2026-09/out
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

python3 -m tools.omr.staged "$PDF" --pages "$PAGE" --weights "$W" \
    --no-surya --no-ocr --out "$OUT/arm-$TAG.record.json"
python3 -m tools.omr.staged.export "$OUT/arm-$TAG.record.json" \
    --out "$OUT/arm-$TAG.musicxml"
echo "=== ARM DONE $TAG ==="
