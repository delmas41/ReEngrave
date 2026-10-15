#!/bin/sh
# 2.136 step 1: the two records, one after the other (one gather-sized load at a time).
B=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a45c68acb647eb29e/benchmarks/omr-bar-sum-holdout-2026-09
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a45c68acb647eb29e
python3 $B/probe/reconcile_gates_2_136.py $R/beethoven5-litolff-mvt1-whole-20261014-night.record.json --label lit --out $B/out/2.136/lit-gates.json > $B/out/2.136/lit.log 2>&1
python3 $B/probe/reconcile_gates_2_136.py $R/brahms1-breitkopf-mvt1-whole-20261014-night.record.json --label brah --out $B/out/2.136/brah-gates.json > $B/out/2.136/brah.log 2>&1
