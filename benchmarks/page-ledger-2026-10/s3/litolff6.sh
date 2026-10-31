#!/bin/sh
# Litolff pages 1-6 gathered (GATHER only, --no-surya), OMR_PAGE_MARKS + OMR_PAGE_OWNER ON: the pool of clean on-line head shapes reaches its minimum
# (8) only by about page 4-6 of this plate (1,2,4,6 left every far head `no_page_shape`), so tile 11's head (p4) can be read. The ON rows carry the
# unfiltered reading beside the filtered one, so no OFF arm is needed for the ledger evidence.
cd "$(dirname "$0")/../../.."
W=${W:-/private/tmp/s3work}
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OMR_PAGE_MARKS=1 OMR_PAGE_OWNER=1 python3 -m tools.omr.staged "$L" --pages 1,2,3,4,5,6 --dpi 600 --weights auto --route-weights \
  --cell-map $LIB/_shared-records/cell-maps --no-surya --through gather --out "$W/litolff6.on.gathered.record.json" > "$W/litolff6.on.log" 2>&1
echo "litolff6 on exit $?"
