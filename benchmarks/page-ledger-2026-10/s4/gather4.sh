#!/bin/sh
# 2.240 step 3: Litolff pages 2,4,6,16 gathered (GATHER only, --no-surya), so p4's far heads read with a pooled head shape (page 16 releases
# the held pages; FINDINGS s2 r2). ARG1 = tag. Records go to $W (not committed).
cd "$(dirname "$0")/../../.."
W=${W:-/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-2.240-s4/work}
mkdir -p "$W"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
python3 -m tools.omr.staged "$L" --pages 2,4,6,16 --dpi 600 --weights auto --route-weights \
  --cell-map $LIB/_shared-records/cell-maps --no-surya --through gather --out "$W/litolff16.$1.gathered.record.json" > "$W/litolff16.$1.log" 2>&1
echo "litolff16 $1 exit $?"
