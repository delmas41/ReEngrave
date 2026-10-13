#!/bin/sh
# 2.97 after the clean-heads guard: the three arms again, ONE AT A TIME.
#   sh chain3_runs_2_97.sh <scratch dir holding arm4/>
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0 OMR_NARROWED_BAR=1
cd "$S/arm4" && PAGES_MAX=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../b01-arm4-report.json ../b01-arm4.musicxml ../b01-arm4.pkl > ../b01-arm4.log 2>&1
cd "$S/arm4" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-arm4-report.json ../lit-arm4.musicxml ../lit-arm4.pkl > ../lit-arm4.log 2>&1
cd "$S/arm4" && python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-arm4-report.json ../brah-arm4.musicxml ../brah-arm4.pkl > ../brah-arm4.log 2>&1
