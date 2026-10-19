#!/bin/sh
# 2.169: serial. Logs land in $OUT/s169_*.log; the big json beside them. Order: Litolff reach, Litolff replay, Litolff causes, Brahms reach, Brahms replay.
OUT=/private/tmp/claude-501
P=benchmarks/omr-stem-refusals-2026-10/probe
rm -f $OUT/s169_alldone
python3 $P/reach_2_169.py litolff $OUT/s169_litolff.json $OUT/s169_reach_litolff.json > $OUT/s169_reach_litolff.log 2>&1
python3 $P/replay_2_169.py litolff $OUT/s169_litolff.json $OUT/s169_reach_litolff.json $OUT/s169_replay_litolff > $OUT/s169_replay_litolff.log 2>&1
python3 $P/causes_2_169.py litolff $OUT/s169_litolff.json $OUT/s169_causes_litolff.json > $OUT/s169_causes_litolff.log 2>&1
python3 $P/reach_2_169.py brahms $OUT/s169_brahms.json $OUT/s169_reach_brahms.json > $OUT/s169_reach_brahms.log 2>&1
python3 $P/replay_2_169.py brahms $OUT/s169_brahms.json $OUT/s169_reach_brahms.json $OUT/s169_replay_brahms > $OUT/s169_replay_brahms.log 2>&1
echo ALLDONE > $OUT/s169_alldone
