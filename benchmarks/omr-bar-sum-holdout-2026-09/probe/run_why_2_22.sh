#!/bin/sh
# ROADMAP 2.22: reconcile_duration diagnosis + crop geometry, one record.
#   sh run_why_2_22.sh litolff|brahms [suffix]
cd "$(dirname "$0")/../../.." || exit 1
R=benchmarks/omr-bar-sum-holdout-2026-09/out/r222
S=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
case "$1" in
  litolff) REC="$S/beethoven5-litolff-mvt1-whole-20260929.record.json" ;;
  brahms) REC="$S/brahms1-breitkopf-mvt1-whole-20260929.record.json" ;;
  *) echo "which?"; exit 2 ;;
esac
export OMR_SURYA_KEEP_ALIVE=0
nohup python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/reconcile_why_2_22.py \
  "$REC" --label "$1$2" --out "$R/$1$2-reconcile-why.json" > "$R/$1$2-why.log" 2>&1 &
echo started
