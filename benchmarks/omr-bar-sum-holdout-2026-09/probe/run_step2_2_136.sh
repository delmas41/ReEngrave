#!/bin/sh
# 2.136 step 2: the two records, one after the other (one load at a time).
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a334355f0930b05c4
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
O=$W/benchmarks/omr-bar-sum-holdout-2026-09/out/2.136-step2
cd $W
python3 $W/benchmarks/omr-bar-sum-holdout-2026-09/probe/step2_2_136.py $R/beethoven5-litolff-mvt1-whole-20261014-night.record.json --label lit --out $O/lit.json > $O/lit.log 2>&1
python3 $W/benchmarks/omr-bar-sum-holdout-2026-09/probe/step2_2_136.py $R/brahms1-breitkopf-mvt1-whole-20261014-night.record.json --label brah --out $O/brah.json > $O/brah.log 2>&1
