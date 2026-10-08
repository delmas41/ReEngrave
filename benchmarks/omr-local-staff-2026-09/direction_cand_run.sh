#!/bin/bash
# per-candidate OCR texts on the 10 held-out pages (diagnosis). OUTDIR default = r1 dir.
L=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$L/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BR=$L/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
O=${OUTDIR:-benchmarks/omr-local-staff-2026-09/out/direction_cap_r1}
P=benchmarks/omr-local-staff-2026-09
for p in ${LIT_PAGES:-4 6 9 12 15}; do python3 $P/direction_cand_texts.py "$LIT" $p $O/cand_lit_$p.json > $O/cand_lit_$p.log 2>&1; done
for p in ${BR_PAGES:-3 7 12 18 24}; do python3 $P/direction_cand_texts.py "$BR" $p $O/cand_br_$p.json > $O/cand_br_$p.log 2>&1; done
