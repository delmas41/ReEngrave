#!/bin/sh
# ROADMAP 2.22: dump every held bar of both whole-movement records, own
# verdicts then re-decided on this tree. Unattended; poll out/r222/*.log.
cd "$(dirname "$0")/../../.." || exit 1
R=benchmarks/omr-bar-sum-holdout-2026-09/out/r222
S=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
mkdir -p "$R"
export OMR_SURYA_KEEP_ALIVE=0
nohup python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/held_funnel_mvt_2_22.py \
  "$S/beethoven5-litolff-mvt1-whole-20260929.record.json" \
  --label litolff --out-dir "$R" --redecide --musicxml > "$R/litolff.log" 2>&1 &
nohup python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/held_funnel_mvt_2_22.py \
  "$S/brahms1-breitkopf-mvt1-whole-20260929.record.json" \
  --label brahms --out-dir "$R" --redecide --musicxml > "$R/brahms.log" 2>&1 &
echo started
