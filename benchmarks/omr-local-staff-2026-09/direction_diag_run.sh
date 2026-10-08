#!/bin/bash
# Candidate-finder diagnosis (no OCR) on the 10 held-out pages. OUTDIR must hold data_<tag>.json from direction_cap_run.sh.
L=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$L/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BR=$L/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
O=${OUTDIR:-benchmarks/omr-local-staff-2026-09/out/direction_cap_r1}
P=benchmarks/omr-local-staff-2026-09
for p in ${LIT_PAGES:-4 6 9 12 15}; do
  pts=$P/points/lit_$p.json; [ -f $pts ] || pts=""
  python3 $P/direction_miss_diag.py "$LIT" $p lit_$p $O $pts > $O/diag_lit_$p.log 2>&1
done
for p in ${BR_PAGES:-3 7 12 18 24}; do
  pts=$P/points/br_$p.json; [ -f $pts ] || pts=""
  python3 $P/direction_miss_diag.py "$BR" $p br_$p $O $pts > $O/diag_br_$p.log 2>&1
done
