#!/bin/bash
# Everything in this directory that runs off COMMITTED artefacts — no PDF, no
# detector, no margin reader, no venv. Seconds.
#
# The two arms that need a pipeline run (`run_brahms4_2x2.sh`,
# `run_shapetie_controls.sh`) are separate and want a warm read cache.
set -uo pipefail
cd "$(dirname "$0")/../../.."
P=benchmarks/omr-lineup-swap-2026-09
S=benchmarks/omr-span-reach-2026-09
mkdir -p "$P/out"

# Label dumps: two sources, deliberately. The caches carry every read label with
# its confidence; a composed run's own blob carries what the ALIGNER saw. Both
# are used, and Beethoven 5 is dumped BOTH ways as a cross-check.
python3 $P/probe/dump_labels.py $S/out/brahms4/cache600 --out $P/out/labels-brahms4.json
python3 $P/probe/dump_labels.py $S/out/beet6/cache600   --out $P/out/labels-beet6.json
python3 $P/probe/dump_labels.py benchmarks/omr-slot-alignment-2026-09/out/cache-beet5 \
        --out $P/out/labels-beet5.json
python3 $P/probe/labels_from_blob.py \
        benchmarks/omr-span-composition-2026-09/out/brahms1/-fitsearch-spans-on.json \
        --out $P/out/labels-brahms1.json
python3 $P/probe/labels_from_blob.py \
        benchmarks/omr-span-composition-2026-09/out/beet5/-fitsearch-spans-on.json \
        --out $P/out/labels-beet5-blob.json
python3 $P/probe/lineups_from_corpus.py beet5   --out $P/out/lineups-beet5.json
python3 $P/probe/lineups_from_corpus.py brahms1 --out $P/out/lineups-brahms1.json

{
echo "################ 1. SUPPORT PROFILES (the signal, and its noise floor)"
python3 $P/probe/changepoint.py $P/out/labels-brahms4.json --spans 0-40,41-98
python3 $P/probe/changepoint.py $P/out/labels-beet5.json   --spans 1-43,44-87
python3 $P/probe/changepoint.py $P/out/labels-beet6.json   --spans 0-26,27-45,46-78
python3 $P/probe/changepoint.py $P/out/labels-brahms1.json --spans 0-44,45-85

echo; echo "################ 2. THE RULE — flag off vs on, five label dumps"
python3 $P/probe/run_spans.py $P/out/labels-brahms4.json $P/out/labels-beet5.json \
        $P/out/labels-beet6.json $P/out/labels-brahms1.json $P/out/labels-beet5-blob.json

echo; echo "################ 3. EXPRESSIBILITY — can the reference SAY the lineup?"
python3 $P/probe/expressibility.py $S/brahms4-lineups.json $S/beet6-lineups.json \
        $P/out/lineups-beet5.json $P/out/lineups-brahms1.json

echo; echo "################ 4. CEILING — what any span rule could reach"
python3 $P/probe/ceiling.py $P/out/brahms4/swap0-spans-on.json --lineups $S/brahms4-lineups.json

echo; echo "################ 5. THE REFERENCE TIE-BREAK, off committed labels"
python3 $P/probe/tiebreak_ceiling.py $P/out/labels-brahms4.json --lineups $S/brahms4-lineups.json
python3 $P/probe/tiebreak_ceiling.py $P/out/labels-brahms1.json --lineups $P/out/lineups-brahms1.json

echo; echo "################ 6. IDENTITY, per region, per arm (Brahms 4)"
D=$P/out/brahms4
python3 $P/probe/score_arms.py --lineups $S/brahms4-lineups.json \
    "no-spans=$D/swap0-spans-off.json" "shipped=$D/swap0-spans-on.json" \
    "swap=$D/swap1-spans-on.json" "shapetie=$D/shapetie-swap0-spans-on.json" \
    "shapetie+swap=$D/shapetie-swap1-spans-on.json"
} 2>&1 | tee $P/out/report.txt
echo "-> $P/out/report.txt"
