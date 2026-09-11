#!/bin/bash
# The GATHER + ADJUDICATE + EVALUATE run that produces the record this
# artefact is built from. Export is a SEPARATE step (export_arm.sh), on the
# manager log's instruction: `staged/__main__.py` imports the exporter AFTER
# the gather, so a mid-run edit reaches it -- and a module imported at process
# START keeps its code, so a mid-run edit silently does NOT. Splitting the two
# means neither hazard can touch this record.
#
# ⚠️ OMR_SURYA_KEEP_ALIVE=0 so this run OWNS its worker and can repair itself.
# NEVER `pkill -f` anything here: one machine has one shared Surya server and
# killing it by name has already cost a sibling agent a multi-hour run.
#
#   bash benchmarks/omr-cleanup-count-2026-09/run_gather.sh 1-4 p1-p4
set -euo pipefail
cd "$(dirname "$0")/../.."

PAGES="${1:-1-4}"
TAG="${2:-p1-p4}"
OUT="benchmarks/omr-cleanup-count-2026-09/out"
mkdir -p "$OUT"

PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

export OMR_SURYA_KEEP_ALIVE=0

echo "start  $(date -u +%FT%TZ)  pages=$PAGES" | tee "$OUT/gather-$TAG.timing"
python3 -u -m tools.omr.staged "$PDF" --pages "$PAGES" --weights "$W" \
    --out "$OUT/record-$TAG.json" --progress 2>&1 | tee "$OUT/gather-$TAG.log"
echo "end    $(date -u +%FT%TZ)" | tee -a "$OUT/gather-$TAG.timing"
