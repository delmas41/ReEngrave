#!/bin/bash
# ROADMAP 2.6 — ONE REAL BASE-VS-ARM GATHER, the control that the record-side
# recompute (`regather_ownership.py`) matches a gather that actually ran.
#
# ⚠️ BASE AND ARM ON ONE TREE (CLAUDE.md §6b). The base arm is produced by
# writing `<BASE_REF>:tools/omr/staged/gather.py` over the working file for the
# duration of that run and restoring it immediately after; every other file,
# the weights, the PDF, the DPI and the flags are identical. A backup is taken
# first and the restore runs on EXIT, including on a failed run.
#
# ⚠️ EACH ARM ITS OWN `--out`. `scan_eval` caches by default and a cached A/B
# reports "identical on every row"; nothing here is cached, and separate output
# paths mean neither arm can be read as the other.
#
# ⚠️ `--no-surya --no-ocr`: identity is NOT what is being measured, and this
# keeps the run off the shared Surya/llama server. NEVER pkill anything.
#
# WARNING: THE DEFAULT REF IS A SHA. The remote-tracking main ref moved nine
# times during the session that built this and twice took `gather.py` with it,
# so a base arm named by a branch cannot be reproduced.
#
#   bash benchmarks/omr-owner-domain-2026-09/real_gather_pair.sh [page] [ref]
set -euo pipefail
cd "$(dirname "$0")/../.."

PAGE="${1:-3}"
BASE_REF="${2:-848dda47}"
OUT="benchmarks/omr-owner-domain-2026-09/out"
mkdir -p "$OUT"

PDF=library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
GATHER=tools/omr/staged/gather.py
BACKUP="$(mktemp -t gather_arm_backup)"

cp "$GATHER" "$BACKUP"
restore() { cp "$BACKUP" "$GATHER"; }
trap restore EXIT

export OMR_SURYA_KEEP_ALIVE=0

echo "== ARM (this tree) =="
date -u +%FT%TZ
python3 -u -m tools.omr.staged "$PDF" --pages "$PAGE" --weights "$W" \
    --no-surya --no-ocr --out "$OUT/real-p$PAGE-arm.json" --progress \
    2>&1 | tee "$OUT/real-p$PAGE-arm.log"
date -u +%FT%TZ

echo "== BASE ($BASE_REF) =="
git show "$BASE_REF:$GATHER" > "$GATHER"
date -u +%FT%TZ
python3 -u -m tools.omr.staged "$PDF" --pages "$PAGE" --weights "$W" \
    --no-surya --no-ocr --out "$OUT/real-p$PAGE-base.json" --progress \
    2>&1 | tee "$OUT/real-p$PAGE-base.log"
date -u +%FT%TZ
restore

echo "== both arms written to $OUT =="
