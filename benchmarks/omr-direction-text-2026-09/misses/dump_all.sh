#!/bin/bash
L=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$L/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BR=$L/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
O=${OUTDIR:-/private/tmp/dtmiss}
for p in 4 6 9 12 15; do python3 benchmarks/omr-direction-text-2026-09/misses/dump_page.py "$LIT" $p lit_$p $O > $O.lit_$p.log 2>&1; done
for p in 3 7 12 18 24; do python3 benchmarks/omr-direction-text-2026-09/misses/dump_page.py "$BR" $p br_$p $O > $O.br_$p.log 2>&1; done
echo done > $O.done
