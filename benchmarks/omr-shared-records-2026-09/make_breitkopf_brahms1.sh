#!/bin/sh
# Build the SHARED staged record for Breitkopf & Härtel Brahms 1 mvt 1, pdf p0-3.
#
# ⚠️ The artefact is MACHINE-LOCAL by design: `library/` is gitignored and a
# staged record is ~100-200 MB. What is committed is this recipe and the
# receipt in FINDINGS.md -- never the JSON.
#
# ⚠️ RUN IT FROM A CLEAN TREE. `staged/__main__.py` stamps provenance AFTER the
# run, so any edit made while it is running -- including an untracked file
# under benchmarks/ -- lands in the record as `dirty: true` and costs the
# artefact its value as a shared baseline.
#
# ⚠️ NO `--musicxml`. The exporter is imported AFTER the gather, so a long run
# dies at the export step on whatever export.py says at that moment. Export
# separately from the record.
#
# ⚠️ `--surya --ocr` is the point. The free text-layer rung reads ZERO labels
# on a 19th-century scan; without the OCR rungs Q.MARGIN_LABEL stays empty,
# `instrument` abstains no_evidence on every staff, `slot_index` collapses to
# the staff ordinal and the part join grafts.
#
# ⚠️ NEVER `pkill -f llama-server`. The Surya keep-alive server is shared and
# killing it has already destroyed a sibling agent's multi-hour run. Check with
#   python3 -m tools.omr.staff_labels_surya --check
# and ATTACH to whatever is up.
set -eu

ROOT=/Users/seanjohnson/Desktop/ReEngrave
PDF="$ROOT/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
W="$ROOT/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
OUT="$ROOT/library/_shared-records/brahms1-breitkopf-p0-p3.record.json"

mkdir -p "$ROOT/library/_shared-records"
python3 -u -m tools.omr.staged "$PDF" --pages 0-3 --weights "$W" \
    --surya --ocr --progress --out "$OUT"
