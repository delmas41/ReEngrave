#!/bin/bash
# ROADMAP 2.261: the three flags, each OFF vs ON through the shared lane report on its own 2-page-per-plate sample. Unattended; one at a time.
# ONLY=1|2|3 runs one. Run from the worktree root.
export OMR_SURYA_KEEP_ALIVE=0
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
for spec in "1 OMR_HAIRPIN_NOT_A_BEAM" "2 OMR_WORD_RETRY_SPARES_HEADS" "3 OMR_CLEF_CARRY_STRONG_STOP"; do
  set -- $spec
  if [ -n "$ONLY" ] && [ "$ONLY" != "$1" ]; then continue; fi
  LANE_REPORT_SAMPLE=benchmarks/hairpin-reach-2026-11/sample-261-fix$1.json \
    python3 -m tools.omr.staged.lane_report --flag $2 --from gather --cell-map master --out out/2.261-fix$1 \
    > benchmarks/hairpin-reach-2026-11/reports/261_fix$1.report.txt 2>&1
  echo "fix $1 done" >> benchmarks/hairpin-reach-2026-11/reports/261_progress.txt
done
