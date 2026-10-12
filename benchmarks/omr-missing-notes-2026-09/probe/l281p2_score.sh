#!/usr/bin/env bash
# l281p2_score: ROADMAP 2.81 PHASE 2. Score ONE small-re-gather record (acceptance_quick --full, through INFER)
# on Sean's hand truth with the Phase 1 scorer, unchanged.  MACHINE-LOCAL (needs the quick record).
#
#   probe/l281p2_score.sh RECORD TAG OUTDIR
#
# Prints, for the page-0 members of the 2.81 population: the Phase 1 strata AND "final state of the judged
# members" = (truth judge, stage that last wrote the duration, outcome, beam level) -- the table that says
# how many bare-stem heads ended DECIDED right / DECIDED wrong / still NARROWED.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REC="$1"; TAG="$2"; OUT="$3"
mkdir -p "$OUT"
for w in obs abs ver prov; do
  python3 "$HERE/l281_extract.py" --what "$w" --record "$REC" --out "$OUT/$TAG-$w.json" > /dev/null
done
python3 "$HERE/l281_population.py" --tag "$TAG" --ext "$OUT" --json "$OUT/$TAG-pop.json" \
  --csv "$OUT/population-$TAG.csv" > "$OUT/population-$TAG.txt"
python3 "$HERE/l281_score.py" --tag "$TAG" --ext "$OUT" --json "$OUT/$TAG-p0-scored.json" > "$OUT/hand-truth-score-$TAG.txt"
python3 "$HERE/l281_later.py" --ext "$OUT" --tag "$TAG" --scored "$OUT/$TAG-p0-scored.json" > "$OUT/later-stages-$TAG.txt"
echo "wrote $OUT/hand-truth-score-$TAG.txt, $OUT/later-stages-$TAG.txt, $OUT/population-$TAG.txt"
