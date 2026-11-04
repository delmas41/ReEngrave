#!/bin/bash
# ROADMAP 2.261 fix 3 (EVALUATE/EXPORT flag): the same GATHER rows re-adjudicated with the flag OFF and ON (readjudicate.py clears the
# verdicts), then the lane report pairs the two records (reuse_gathers.py). Isolates the flag from OCR draws between two gathers.
# Run from the worktree root: bash same_gather_261.sh PLATE
export OMR_SURYA_KEEP_ALIVE=0
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export LANE_REPORT_SAMPLE=benchmarks/hairpin-reach-2026-11/sample-261-fix3.json
P=$1
D=out/2.261-fix3-same-$P
mkdir -p $D
OMR_CLEF_CARRY_STRONG_STOP=0 python3 benchmarks/hairpin-reach-2026-11/readjudicate.py out/2.261-fix3/work/$P.off.gathered.record.json $D/off.record.json
OMR_CLEF_CARRY_STRONG_STOP=1 python3 benchmarks/hairpin-reach-2026-11/readjudicate.py out/2.261-fix3/work/$P.off.gathered.record.json $D/on.record.json
python3 benchmarks/hairpin-reach-2026-11/reuse_gathers.py $D/off.record.json $D/on.record.json -- --flag OMR_CLEF_CARRY_STRONG_STOP --plates $P --from gather --cell-map master --out $D/lr > benchmarks/hairpin-reach-2026-11/reports/261_fix3_${P}_same_gather.report.txt 2>&1
echo "same $P done" >> benchmarks/hairpin-reach-2026-11/reports/261_progress.txt
