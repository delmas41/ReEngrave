#!/bin/sh
# Litolff pages 2,4,6,16 (GATHER only, --no-surya, owner ON). Page 16 alone holds 9 clean on-line heads (the night record's `page n=9`), which
# reaches the pool minimum (8) and releases the held pages 2,4,6, so their far heads are READ (pages 1-6 alone never reached it: every far head
# `no_page_shape`). Waits for written_on.sh.
cd "$(dirname "$0")/../../.."
W=${W:-/private/tmp/s3work}
while ! grep -q "litolff on exit" benchmarks/page-ledger-2026-10/s3/written_on.log 2>/dev/null; do sleep 20; done
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
OMR_PAGE_MARKS=1 OMR_PAGE_OWNER=1 python3 -m tools.omr.staged "$L" --pages 2,4,6,16 --dpi 600 --weights auto --route-weights \
  --cell-map $LIB/_shared-records/cell-maps --no-surya --through gather --out "$W/litolff16.on.gathered.record.json" > "$W/litolff16.on.log" 2>&1
echo "litolff16 on exit $?"
