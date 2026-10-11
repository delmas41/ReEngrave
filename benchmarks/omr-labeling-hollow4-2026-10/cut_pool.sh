#!/bin/bash
# ROADMAP 2.4b step 3a -- cut the candidate POOL (machine time; no labelling yet).
# Cells are cut by the hollow2 cutter: seeded random sample, the PIPELINE's own padding, 600 dpi.
# Pages are 1-BASED here (the cutter's convention). None is a held-out hand-truth page
# (data/hand-truth/held-out.json: 317803 idx 0,1 / 984073 idx 2,3 / 405834 idx 4) and none is the
# plan's gate page (984073 idx 1); build_batch.py refuses them again as a control.
# Pages already used by earlier labelling rounds are avoided where the manifests say so.
set -eu
cd "$(dirname "$0")/../.."
E=/Users/seanjohnson/Desktop/ReEngrave/library/editions
POOL=${1:-scratch/hollow4-pool}
N=${N:-14}
PLAN=""
add() { PLAN="$PLAN${PLAN:+,}$1=$2:$3:$N"; }
BRA=$E/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
LIT=$E/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
SIM=$E/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf
PET=$E/mahler/symphony-5-gmw-44/mahler--symphony-5-gmw-44--peters-1919--imslp112218.pdf
ELG1=$E/elgar/symphony-1-op55/elgar--symphony-1-op55--novello-co-1908--imslp56155.pdf
ELG2=$E/elgar/symphony-2-op63/elgar--symphony-2-op63--novello-co-1911--imslp979455.pdf
EUL=$E/rimsky-korsakov/scheherazade-op35/rimsky-korsakov--scheherazade-op35--eulenburg--imslp1010338.pdf
TCH=$E/tchaikovsky/symphony-5-op64/tchaikovsky--symphony-5-op64--breitkopf-hartel-1930--imslp504184.pdf
MAH=$E/mahler/symphony-1-gmw-11/mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf
for p in 21 31 45; do add brahms $BRA $p; done
for p in 9 13 25 53; do add litolff $LIT $p; done
for p in 25 41 61; do add simrock $SIM $p; done
for p in 31 51; do add peters $PET $p; done
for p in 21 41; do add elgar1 $ELG1 $p; done
add elgar2 $ELG2 31
for p in 31 101; do add eulenburg $EUL $p; done
for p in 31 61; do add tchaik5 $TCH $p; done
for p in 41 81; do add mahler1 $MAH $p; done
echo "$PLAN" | tr ',' '\n' | wc -l | xargs echo "pages in plan:"
PYTHONPATH=. python3 benchmarks/omr-labeling-hollow2-2026-09/cut_candidate_cells.py --out-dir "$POOL" --plan "$PLAN" --dpi 600
