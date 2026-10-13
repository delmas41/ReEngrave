#!/usr/bin/env bash
# 2.4b re-assembly A/B: gather the four reverse-graft arms (lock + trap for the overnight re-gather).
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
LOCK=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/.training-2.4b.lock
trap 'rm -f "$LOCK"' EXIT INT TERM
echo "2.4b reverse-ab pid $$ $(date -u +%FT%TZ)" > "$LOCK"
C=omr-weights/candidates
bash benchmarks/omr-labeling-hollow4-2026-10/run_2.4b_ab.sh \
  revC=$C/hollow4-2.4b-REVERSE-withv24-armC-bn-2026-10-13.pt ctlC=$C/hollow4-2.4b-REVERSE-control-armC-bn-2026-10-13.pt
mv benchmarks/omr-labeling-hollow4-2026-10/ab/rec-*.json runs/2.4b/ab-records/ 2>/dev/null
echo DONE
