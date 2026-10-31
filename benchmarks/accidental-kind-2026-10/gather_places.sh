#!/bin/zsh
# 2.247 r2: GATHER the pages of Sean's r1 tile places with the flag ON (master cells, shared detector cache), small: one arm, few pages.
# usage: gather_places.sh OUTDIR FLAGVALUE   (records OUTDIR/<plate>.k<FLAGVALUE>.record.json)
set -e
OUT=$1; K=$2
mkdir -p $OUT
LIB=library/editions
export OMR_SURYA_KEEP_ALIVE=0 OMR_ACCIDENTAL_KIND=$K OMR_DETECTOR_CACHE=library/_shared-records/detector-cache
python3 -u -m tools.omr.staged $LIB/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --pages 2,4,10 --dpi 600 --weights auto --route-weights --cell-map library/_shared-records/cell-maps --out $OUT/litolff.k$K.record.json > $OUT/litolff.k$K.log 2>&1
python3 -u -m tools.omr.staged "$(python3 -c 'import sys; sys.path.insert(0,"."); from tools.omr.staged import lane_report as L; print(L.LIB / L.PLATES["brahms"]["pdf"])')" \
  --pages 4,12,19 --dpi 600 --weights auto --route-weights --cell-map library/_shared-records/cell-maps --out $OUT/brahms.k$K.record.json > $OUT/brahms.k$K.log 2>&1
echo done
