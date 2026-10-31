#!/bin/sh
# 2.240 s2 round 2: Litolff pages 1,2,4,6 gathered (stage GATHER only, --no-surya) OFF vs ON, so p4's far heads have a pooled head shape (the
# 2-page lane-report arm had none: tile 11's head was `no_page_shape` there). Records go to $W (not committed).
cd "$(dirname "$0")/../../.."
W=${W:-/private/tmp/s3work}
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
for arm in off on; do
  if [ $arm = on ]; then V=1; else V=0; fi
  OMR_PAGE_MARKS=$V OMR_PAGE_OWNER=$V python3 -m tools.omr.staged "$L" --pages 1,2,4,6 --dpi 600 --weights auto --route-weights \
    --cell-map $LIB/_shared-records/cell-maps --no-surya --through gather --out "$W/litolff4.$arm.gathered.record.json" > "$W/litolff4.$arm.log" 2>&1
  echo "litolff4 $arm exit $?"
done
