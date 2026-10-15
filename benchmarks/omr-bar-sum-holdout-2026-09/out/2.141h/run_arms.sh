#!/bin/bash
# serial: both movements, 5 arms. base = W2 only (+ --control). usage: run_arms.sh [lit|brah] ...
cd "$(dirname "$0")/../../../.."
R=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records
O=benchmarks/omr-bar-sum-holdout-2026-09/out/2.141h/arms
P=benchmarks/omr-bar-sum-holdout-2026-09/probe/arm_2_141h.py
export OMR_INFER_CARRIED_METER_FIX=1 OMR_INFER_LEDGER_OWNER_HEADS=1
for mov in "$@"; do
  case $mov in lit) rec=$R/beethoven5-litolff-mvt1-whole-20261014-night.record.json;; brah) rec=$R/brahms1-breitkopf-mvt1-whole-20261014-night.record.json;; esac
  for arm in base f1 f2 f3 all; do
    [ -f $O/$mov-$arm/durations.json ] && continue
    case $arm in base) E="";; f1) E="OMR_BEAM_LEVEL_STROKE_IS_A_BEAM=1";; f2) E="OMR_OWN_STEM_UNISON_BOTH=1";; f3) E="OMR_WHOLE_REST_INK_LEAVES_BAR=1";; all) E="OMR_BEAM_LEVEL_STROKE_IS_A_BEAM=1 OMR_OWN_STEM_UNISON_BOTH=1 OMR_WHOLE_REST_INK_LEAVES_BAR=1";; esac
    C=""; [ $arm = base ] && C="--control"
    echo "== $mov $arm"; env $E python3 $P $rec $O/$mov-$arm $C 2>&1 | tail -8
  done
done
