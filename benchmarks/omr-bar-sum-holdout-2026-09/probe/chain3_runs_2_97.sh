#!/bin/sh
# 2.97 after the clean-heads guard: the three arms again, ONE AT A TIME.
#   sh chain3_runs_2_97.sh <scratch dir holding arm3/>
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0 OMR_NARROWED_BAR=1
cd "$S/arm3" && PAGES_MAX=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../b01-arm3-report.json ../b01-arm3.musicxml ../b01-arm3.pkl > ../b01-arm3.log 2>&1
cd "$S/arm3" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-arm3-report.json ../lit-arm3.musicxml ../lit-arm3.pkl > ../lit-arm3.log 2>&1
cd "$S/arm3" && python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-arm3-report.json ../brah-arm3.musicxml ../brah-arm3.pkl > ../brah-arm3.log 2>&1
