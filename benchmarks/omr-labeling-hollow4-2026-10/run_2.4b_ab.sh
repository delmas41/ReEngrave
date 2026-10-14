#!/usr/bin/env bash
# ROADMAP 2.4b step 3 -- the 2.34 harness's own gather command (`run_ab.sh`: --through adjudicate --no-surya --no-ocr),
# one record per (arm, document page), then score_ab.py against Sean's hollow truth.
#   usage: run_2.4b_ab.sh label=weights [label=weights ...]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
E=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$E/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRA=$E/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
OUT=benchmarks/omr-labeling-hollow4-2026-10/ab
mkdir -p "$OUT"
for arm in "$@"; do
  L="${arm%%=*}"; W="${arm#*=}"
  for spec in "lit:$LIT:1" "bra:$BRA:0"; do
    IFS=: read -r tag pdf pg <<<"$spec"
    [ -s "$OUT/rec-$tag-$L.json" ] && { echo "have $tag $L"; continue; }
    echo "=== $L $tag p$pg ($(date +%T))"
    nice -n 10 python3 -m tools.omr.staged "$pdf" --pages "$pg" --weights "$W" --through adjudicate --no-surya --no-ocr \
        --out "$OUT/rec-$tag-$L.json" >/dev/null 2>"$OUT/log-$tag-$L.txt"
  done
done
