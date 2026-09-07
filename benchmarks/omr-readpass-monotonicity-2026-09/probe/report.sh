#!/bin/bash
# Every arm this benchmark made, through the phase-0 identity scorer.
set -u
cd "$(dirname "$0")/../../.." || exit 1
OUT=benchmarks/omr-readpass-monotonicity-2026-09/out
python3 benchmarks/omr-readpass-monotonicity-2026-09/probe/score_arms.py beet5 \
  benchmarks/omr-absent-instrument-veto-2026-09/out/whole-report2.extract.json \
  "$OUT/whole-identity.normalized.json" \
  benchmarks/omr-slot-alignment-2026-09/out/-map-spans-on.json \
  "$OUT/arm-full973.json" \
  "$OUT/arm-minus11-962.json" \
  "$OUT/arm-full973-structure-only.json" \
  "$OUT/arm-full973-clefs.json" \
  "$OUT/arm-minus11-962-clefs.json" \
  "$OUT/arm-full973-clefs-readers-only.json" \
  "$OUT/arm-7ea27a4b-962-noclefs.json" \
  "$OUT/arm-7ea27a4b-962-clefs.json" \
  | sed -n '1,14p'
