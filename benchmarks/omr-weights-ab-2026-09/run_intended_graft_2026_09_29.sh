#!/usr/bin/env bash
# Sean said "Run A": the graft INTENDED on 2026-09-04, built with the FIXED
# merge_class_head.py (2.34/2026-09-29), compared against today's production
# with the same tool's own harness (run_ab.sh, --through adjudicate).
#
# Candidate: omr-weights/candidates/hollow-graft-intended-2026-09-29.pt
#   = base hollow-ft-2026-09-03.pt + ONLY the 7 kept hollow-notehead rows
#     from round5-sweep/distill25/epoch0.pt, bias-shift 0.9 -- the exact
#     command in docs/handoff-2026-09-04-round5-class-collapse.md:65-71,
#     run through the tool that no longer does the graft backwards.
#   Verified (see verify step below): 589/595 tensors bit-identical to
#   base; the other 6 (weight+bias for 3 head scales) carry the 7 kept
#   classes' rows from the fine-tune, bias-shifted -0.9; every non-kept
#   class row inside those same 6 tensors is base's, bit-exact.
#
# Production: omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
#   -- FINDINGS.md section 2: this file's backbone/neck/box-regression are
#   distill25/epoch0's, not hollow-ft-2026-09-03's. The two checkpoints
#   compared here therefore differ in more than the 7 notehead rows; that
#   is the question this run answers, not a confound to control out.
#
# Documents (CLAUDE.md acceptance set), pdf pages 1-4 each, --no-surya:
#   Brahms 1/i, Breitkopf 317803 (SHATTERING plate)
#   Beethoven 5/i, Litolff 984073 (MERGING plate)
#
# Usage: nohup ./run_intended_graft_2026_09_29.sh > out/driver.log 2>&1 &
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BENCH=benchmarks/omr-weights-ab-2026-09
PROD=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
CAND=omr-weights/candidates/hollow-graft-intended-2026-09-29.pt

BRAHMS_PDF="library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
BRAHMS_BASENAME="brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"
LITOLFF_PDF="library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"
LITOLFF_BASENAME="beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"

echo "=== $(date) driver starting ==="

# Each run_ab.sh call writes to out/<label_a>-vs-<label_b>/ -- labels are
# suffixed per document so the Brahms and Litolff runs never collide.

echo "--- control: production vs production, Brahms p1 (must be zero diffs) ---"
"$BENCH/run_ab.sh" "$BRAHMS_PDF" 1 \
    production-control=$PROD production-control_copy=$PROD \
    "$BRAHMS_BASENAME"

echo "--- Brahms 1/i (317803), pages 1-4: production vs intended graft ---"
"$BENCH/run_ab.sh" "$BRAHMS_PDF" 1-4 \
    production-brahms=$PROD candidate-brahms=$CAND \
    "$BRAHMS_BASENAME"

echo "--- Litolff 984073, pages 1-4: production vs intended graft ---"
"$BENCH/run_ab.sh" "$LITOLFF_PDF" 1-4 \
    production-litolff=$PROD candidate-litolff=$CAND \
    "$LITOLFF_BASENAME"

echo "--- hollow axis: Beethoven 5 p1 (Litolff 984073), half-notes of 68 ---"
python3 "$BENCH/../omr-labeling-survey-2026-09/hollow_eval.py" \
    --weights $PROD --tag production-intended-2026-09-29 \
    --pdf "$LITOLFF_PDF" --page 1 --stem beet5-p1 --score
python3 "$BENCH/../omr-labeling-survey-2026-09/hollow_eval.py" \
    --weights $CAND --tag candidate-intended-2026-09-29 \
    --pdf "$LITOLFF_PDF" --page 1 --stem beet5-p1 --score

echo "=== $(date) driver finished ==="
echo "Summaries:"
echo "  $BENCH/out/production-control-vs-production-control_copy/TABLE.md  (control, must be zero diffs)"
echo "  $BENCH/out/production-brahms-vs-candidate-brahms/TABLE.md          (Brahms 317803, pages 1-4)"
echo "  $BENCH/out/production-litolff-vs-candidate-litolff/TABLE.md        (Litolff 984073, pages 1-4)"
echo "  $BENCH/../omr-labeling-survey-2026-09/hollow_eval_production-intended-2026-09-29.json"
echo "  $BENCH/../omr-labeling-survey-2026-09/hollow_eval_candidate-intended-2026-09-29.json"
