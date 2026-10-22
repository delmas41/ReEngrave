#!/bin/sh
# ROADMAP 2.164: extract the candidate cells from both night records (serial, read-only)
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
P=benchmarks/omr-head-fill-2026-09/probe/extract_2_164.py
python3 $P $R/beethoven5-litolff-mvt1-whole-20261016-night.record.json out/2.164/tails_litolff.json out/2.164/ext_litolff.json
python3 $P $R/brahms1-breitkopf-mvt1-whole-20261016-night.record.json out/2.164/tails_brahms.json out/2.164/ext_brahms.json
echo done
