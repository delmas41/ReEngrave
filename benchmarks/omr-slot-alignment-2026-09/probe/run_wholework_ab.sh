#!/bin/bash
# Whole-work A/B for the group-mapping fix, sharing ONE read pass.
#
# Arm ORDINAL reproduces the pre-fix behaviour (raw bracket-ordinal comparison);
# arm MAP is the shipped default. The read pass is cached, so arm 2 is cheap and
# -- more importantly -- both arms see byte-identical margin labels, which takes
# the recorded Surya nondeterminism out of a comparison whose whole content is a
# few dozen names.
#
# OMR_SURYA_KEEP_ALIVE=0 on purpose: an unattended run must own its own worker
# rather than depend on the shared keep-alive server it is not allowed to repair.
set -u
cd "$(dirname "$0")/../../.." || exit 1
PDF=/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OUT=benchmarks/omr-slot-alignment-2026-09/out
CACHE=$OUT/cache-beet5
COMPOSE=benchmarks/omr-spans-veto-composition-2026-09/probe/compose.py
EXTRACT=benchmarks/omr-absent-instrument-veto-2026-09/probe/extract.py
SCORE=benchmarks/omr-absent-instrument-veto-2026-09/probe/score_full_systems.py
export OMR_SURYA_KEEP_ALIVE=0
mkdir -p "$CACHE"
for ARM in ordinal map; do
  echo "=== ARM $ARM  $(date -u +%FT%TZ)"
  OMR_SLOT_GROUP_MAP=$ARM python3 -u "$COMPOSE" "$PDF" \
      --out-dir "$OUT" --pages 0-87 --dpi 600 --cache "$CACHE" --tag="-$ARM" \
      2>&1 | tail -5
done
echo "=== SCORING $(date -u +%FT%TZ)"
for f in "$OUT"/*-ordinal*.json "$OUT"/*-map*.json; do
  case "$f" in *extract*) continue;; esac
  [ -f "$f" ] || continue
  e="${f%.json}.extract.json"
  python3 "$EXTRACT" "$f" "$e" >/dev/null 2>&1 && \
    { echo "--- $(basename "$e")"; python3 "$SCORE" beet5 "$e" 2>&1 | sed -n '1,12p'; }
done
echo "=== DONE $(date -u +%FT%TZ)"
