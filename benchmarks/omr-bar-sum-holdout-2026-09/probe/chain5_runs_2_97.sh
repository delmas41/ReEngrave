#!/bin/sh
# 2.97 after the clean-heads guard: the three arms again, ONE AT A TIME.
#   sh chain3_runs_2_97.sh <scratch dir holding arm5/>
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0 OMR_NARROWED_BAR=1
cd "$S/arm5" && PAGES_MAX=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../b01-arm5-report.json ../b01-arm5.musicxml ../b01-arm5.pkl > ../b01-arm5.log 2>&1
cd "$S/arm5" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-arm5-report.json ../lit-arm5.musicxml ../lit-arm5.pkl > ../lit-arm5.log 2>&1
cd "$S/arm5" && python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-arm5-report.json ../brah-arm5.musicxml ../brah-arm5.pkl > ../brah-arm5.log 2>&1
