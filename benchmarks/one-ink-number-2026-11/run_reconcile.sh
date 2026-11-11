#!/bin/bash
# ROADMAP 2.293 step 1: the three figures on the SAME pages. The old readout (2.236 PageInk: the 2.283 / 2.288 / 2.286 numbers all come from it) and the
# new ink number, on the fresh 2.284b-r2 slices and on the stale 20261029-night slices (conservation's default). Output: $OUT/<name>.log
# usage: run_reconcile.sh [OUT_DIR]   (run from the repo root of a worktree; serial; OCR servers off)
OUT=${1:-/private/tmp/claude-501/scratch293/recon}
mkdir -p "$OUT"
export OMR_SURYA_KEEP_ALIVE=0
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
for spec in "brahms-r2|$LIB/claim-readout-slices-2284b-r2-brahms.on.gathered|0" "litolff-r2|$LIB/claim-readout-slices-2284b-r2-litolff.on.gathered|2" \
            "brahms-1029|brahms:20261029-night|0" "litolff-1029|litolff:20261029-night|2"; do
  IFS='|' read -r name rec page <<< "$spec"
  python3 -m tools.omr.staged.claim_readout "$rec" --pages "$page" --out "$OUT/old_$name" > "$OUT/old_$name.log" 2>&1
  python3 -m tools.omr.staged.claim_readout ink "$rec" --pages "$page" --out "$OUT/ink_$name" > "$OUT/ink_$name.log" 2>&1
done
echo done > "$OUT/DONE"
