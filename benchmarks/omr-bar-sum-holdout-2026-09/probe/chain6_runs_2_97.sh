#!/bin/sh
# 2.97: bases on the MERGED main (arm5 tree minus the three staged files), after chain5.
S="$1"
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
export OMR_SURYA_KEEP_ALIVE=0
while pgrep -f chain5_runs_2_97.sh >/dev/null; do sleep 30; done
cd "$S/base5" && PAGES_MAX=1 python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../b01-base5-report.json ../b01-base5.musicxml ../b01-base5.pkl > ../b01-base5.log 2>&1
cd "$S/base5" && python3 run_2_97.py $L/beethoven5-litolff-mvt1-whole-20261011-night.record.json ../lit-base5-report.json ../lit-base5.musicxml ../lit-base5.pkl > ../lit-base5.log 2>&1
cd "$S/base5" && python3 run_2_97.py $L/brahms1-breitkopf-mvt1-whole-20261011-night.record.json ../brah-base5-report.json ../brah-base5.musicxml ../brah-base5.pkl > ../brah-base5.log 2>&1
