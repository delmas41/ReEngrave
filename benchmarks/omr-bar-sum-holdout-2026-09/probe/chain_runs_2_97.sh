#!/bin/sh
# ROADMAP 2.97: the three full re-decides still needed, ONE AT A TIME (the
# machine fell over twice with five heavy jobs at once).
#   sh chain_runs_2_97.sh <scratch dir holding armtree/ and basetree/>
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0
cd "$S/basetree" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-base-report.json ../lit-base.musicxml ../lit-base.pkl > ../lit-base.log 2>&1
cd "$S/armtree" && OMR_NARROWED_BAR=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-arm-report.json ../brah-arm.musicxml ../brah-arm.pkl > ../brah-arm.log 2>&1
cd "$S/basetree" && python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-base-report.json ../brah-base.musicxml ../brah-base.pkl > ../brah-base.log 2>&1
