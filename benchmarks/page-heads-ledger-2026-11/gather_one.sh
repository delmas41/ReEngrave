#!/bin/bash
# ROADMAP 2.290 build: one small page gather on THIS worktree's tree (shared detector cache, master cell map, OCR server off after).
# usage: gather_one.sh PLATE PAGES ARM(off|one|on) OUTDIR [--through adjudicate]
#   off = both 2.290 flags 0; one = OMR_PAGE_HEAD_ONE=1 only; on = OMR_PAGE_HEAD_ONE=1 OMR_PAGE_HEAD_LEDGER=1
# Waits (polling every 30 s) until fewer than two `tools.omr.staged` processes run on the machine (CLAUDE: at most two gathers at once).
# The ON arm also writes the real-case crops (OMR_PAGE_HEAD_CASES_DUMP, real_cases/dump-PLATE.json).
cd "$(dirname "$0")/../.."
W=$(pwd)
R=/Users/seanjohnson/Desktop/ReEngrave/library
PLATE=$1; PG=$2; ARM=$3; OUT=$4; shift 4
if [ "$PLATE" = litolff ]; then PDF=$R/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf; else PDF=$R/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf; fi
ONE=0; LED=0
[ "$ARM" = one ] && ONE=1
[ "$ARM" = on ] && ONE=1 && LED=1
mkdir -p "$OUT"
TAG=$PLATE.p${PG//,/-}.$ARM
while [ "$(ps aux | grep -E 'tools\.omr\.staged' | grep -v grep | wc -l | tr -d ' ')" -ge 2 ]; do sleep 30; done
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$R/_shared-records/detector-cache OMR_PAGE_HEAD_ONE=$ONE OMR_PAGE_HEAD_LEDGER=$LED
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
if [ "$ARM" = on ]; then export OMR_PAGE_HEAD_CASES_DUMP=$W/benchmarks/page-heads-ledger-2026-11/real_cases/dump-$PLATE.json; fi
( time python3 -u -m tools.omr.staged "$PDF" --pages "$PG" --dpi 600 --weights auto --route-weights --cell-map $R/_shared-records/cell-maps --progress --out "$OUT/$TAG.record.json" "$@" ) > "$OUT/$TAG.log" 2>&1
echo "done rc=$?" >> "$OUT/$TAG.log"
