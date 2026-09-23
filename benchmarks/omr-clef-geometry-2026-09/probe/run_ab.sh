#!/bin/bash
# ROADMAP 2.11 — the base-vs-arm gather. A GATHER change is invisible to
# `readjudicate` and `reexport_arm` (CLAUDE.md §4d), so this runs the reader
# TWICE on one page, once with the three changed files restored from the
# commit's parent and once with the commit's own.
#
# ⚠️ ONE TREE, TWO ARMS, IN SEQUENCE. The CLI imports the exporter AFTER the
# gather, so an edit landing mid-run reaches it; the two arms therefore never
# overlap, and each finishes before the next file swap.
# ⚠️ `--no-surya --no-ocr` keeps this off the shared Surya/llama server.
# Nothing here starts or stops a resident process.
#
#   bash benchmarks/omr-clef-geometry-2026-09/probe/run_ab.sh <base-sha> <pdf> <page> <tag>
set -euo pipefail

BASE_SHA="$1"; PDF="$2"; PAGE="$3"; TAG="$4"
OUT=benchmarks/omr-clef-geometry-2026-09/out
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
FILES="tools/omr/clef_locator.py tools/omr/staged/gather.py tools/omr/staged/adjudicators/notehead_precision.py"

mkdir -p "$OUT" /tmp/claude-501/ab-keep
for f in $FILES; do cp "$f" "/tmp/claude-501/ab-keep/$(basename "$f")"; done

echo "=== BASE ($BASE_SHA) ==="
for f in $FILES; do git show "$BASE_SHA:$f" > "$f"; done
python3 -m tools.omr.staged "$PDF" --pages "$PAGE" --weights "$W" \
    --no-surya --no-ocr --out "$OUT/base-$TAG.record.json"
python3 -m tools.omr.staged.export "$OUT/base-$TAG.record.json" \
    --out "$OUT/base-$TAG.musicxml"

echo "=== restore ARM ==="
for f in $FILES; do cp "/tmp/claude-501/ab-keep/$(basename "$f")" "$f"; done
git diff --quiet -- $FILES && echo "arm restored clean" || { echo "TREE DIRTY AFTER RESTORE"; exit 3; }

echo "=== ARM ==="
python3 -m tools.omr.staged "$PDF" --pages "$PAGE" --weights "$W" \
    --no-surya --no-ocr --out "$OUT/arm-$TAG.record.json"
python3 -m tools.omr.staged.export "$OUT/arm-$TAG.record.json" \
    --out "$OUT/arm-$TAG.musicxml"
echo "=== DONE $TAG ==="
