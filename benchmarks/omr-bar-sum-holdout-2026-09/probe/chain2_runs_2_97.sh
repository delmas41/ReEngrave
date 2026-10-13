#!/bin/sh
# 2.97: base arms re-run from a tree identical to the arm's except the three
# staged files (the first base trees were `git archive`, which lacks ignored
# data files the arm tree had -- an invalid A/B: base held 1085 vs 1044).
#   sh chain2_runs_2_97.sh <scratch dir>   (waits for chain_runs_2_97.sh first)
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0
while pgrep -f chain_runs_2_97.sh >/dev/null; do sleep 30; done
cd "$S/basetree" && PAGES_MAX=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../b01-base2-report.json ../b01-base2.musicxml ../b01-base2.pkl > ../b01-base2.log 2>&1
cd "$S/basetree" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-base2-report.json ../lit-base2.musicxml ../lit-base2.pkl > ../lit-base2.log 2>&1
