#!/bin/bash
# usage: gather.sh PLATE PAGES ARM [ENV=VAL ...]
# One small per-page gather --through adjudicate on the tree's defaults (+ env overrides), master cell map + shared detector cache.
# ONE AT A TIME ACROSS THE MACHINE (CLAUDE.md lean lanes). OCR server off after.
set -e
PLATE=$1; PAGES=$2; ARM=$3; shift 3
L=/Users/seanjohnson/Desktop/ReEngrave/library
case $PLATE in
 litolff) PDF=$L/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf;;
 brahms) PDF=$L/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf;;
esac
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$L/_shared-records/detector-cache
for kv in "$@"; do export "$kv"; done
mkdir -p out/stems-rerun
time python3 -u -m tools.omr.staged "$PDF" --pages $PAGES --dpi 600 --weights auto --route-weights --through adjudicate --cell-map $L/_shared-records/cell-maps --out out/stems-rerun/$PLATE.$ARM.record.json
