#!/bin/bash
# Everything this session measures, in SEQUENCE. One process at a time on
# purpose: the machine is shared with other agents and a run that competes for
# CPU with its own control arm is not a control.
set -u
cd "$(dirname "$0")/../.."
: "${SCRATCH:?set SCRATCH}"
export OMR_SURYA_KEEP_ALIVE=0

echo "### 1. census — what does the >= 5 filter actually drop, library-wide"
python3 -u benchmarks/omr-one-line-staves-2026-09/probe_census.py \
    --per-edition 3 --out census.json

echo
echo "### 2. dvorak-sym9-mvt4 — the ONE engraved work with a printed 1-line staff"
bash benchmarks/omr-one-line-staves-2026-09/run_ab.sh dv \
    /Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-orchestral-e2e/fixtures/dvorak-sym9-mvt4.pdf \
    0 --no-direction-text

echo "ALL_DONE"
