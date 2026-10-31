#!/bin/sh
# 2.240 step 3: the frozen lane-report sample (+ its context page) gathered ONCE per plate with the step-3 GATHER tree (ARG1 = a tree from
# snapshot.sh), --no-surya, master cells, the shared detector cache; saved as the night-record name with tag s4g2240 so
# `lane_report --tag s4g2240 --replay-gathered --flag OMR_PAGE_OWNER_READ` replays ADJUDICATE..EXPORT for both arms on the same gather
# (OMR_PAGE_OWNER_READ changes no GATHER row). Serial: one large gather at a time.
cd "$1"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
R=$LIB/_shared-records
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$R/detector-cache
W=$R/lane-2.240-s4/work
python3 -m tools.omr.staged $LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --pages 1,2,4,6,8,9,10,11,16 --dpi 600 --weights auto --route-weights --cell-map $R/cell-maps --no-surya --through gather \
  --out $R/beethoven5-litolff-mvt1-whole-s4g2240.record.json > $W/sample.litolff.log 2>&1
echo "litolff exit $?"
python3 -m tools.omr.staged $LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf \
  --pages 0,4,5,8,12,14,19,25 --dpi 600 --weights auto --route-weights --cell-map $R/cell-maps --no-surya --through gather \
  --out $R/brahms1-breitkopf-mvt1-whole-s4g2240.record.json > $W/sample.brahms.log 2>&1
echo "brahms exit $?"
