#!/usr/bin/env bash
LOCK=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/.training-2.4b.lock
trap 'rm -f "$LOCK"' EXIT INT TERM
echo "2.4b bn-ab $$" > "$LOCK"
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
bash benchmarks/omr-labeling-hollow4-2026-10/run_2.4b_ab.sh bnv24=runs/2.4b/hollow4bn-withv24/weights/last.pt bnctl=runs/2.4b/hollow4bn-control/weights/last.pt
mv benchmarks/omr-labeling-hollow4-2026-10/ab/rec-*.json runs/2.4b/ab-records/; echo DONE
