#!/bin/sh
# 2.169: serial (one page gather at a time). Summary lines land in $OUT/*.log; the big json beside them.
OUT=/private/tmp/claude-501
P=benchmarks/omr-stem-refusals-2026-10/probe
python3 $P/causes_2_169.py litolff $OUT/s169_litolff.json $OUT/s169_causes_litolff.json > $OUT/s169_causes_litolff.log 2>&1
python3 $P/reach_2_169.py litolff $OUT/s169_litolff.json $OUT/s169_reach_litolff.json > $OUT/s169_reach_litolff.log 2>&1
while [ ! -s $OUT/s169_brahms.json ]; do sleep 20; done
python3 $P/reach_2_169.py brahms $OUT/s169_brahms.json $OUT/s169_reach_brahms.json > $OUT/s169_reach_brahms.log 2>&1
python3 $P/causes_2_169.py brahms $OUT/s169_brahms.json $OUT/s169_causes_brahms.json > $OUT/s169_causes_brahms.log 2>&1
echo ALLDONE > $OUT/s169_alldone
