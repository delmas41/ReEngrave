#!/bin/bash
# The SAME four pages as `benchmarks/omr-part-join-phase2-2026-09`, gathered
# with the margin-label reader reachable (`--surya --ocr`), because the
# committed shared record PREDATES the `pdf_path` fix and its `margin_label`
# rows are the 75 abstentions.
#
# ⚠️ NO `--musicxml`: the exporter is imported AFTER the gather, so a mid-run
# edit reaches it. Export separately.
# ⚠️ OMR_SURYA_KEEP_ALIVE=0 so this run OWNS its worker. NEVER `pkill -f`.
set -euo pipefail
cd "$(dirname "$0")/../.."

OUT=benchmarks/omr-slot-index-2026-09/out
mkdir -p "$OUT"
PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

export OMR_SURYA_KEEP_ALIVE=0
echo "start $(date -u +%FT%TZ)"
python3 -u -m tools.omr.staged "$PDF" --pages 1-4 --weights "$W" --surya --ocr \
    --out "$OUT/record-labels.json" --progress
echo "end   $(date -u +%FT%TZ)"
