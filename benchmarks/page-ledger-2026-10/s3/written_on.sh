#!/bin/sh
# 2.240 s2 round 2: the WRITTEN ON record (full pipeline, --no-surya) of the sample pages, for `page_owner compare` (the old cell-copy rules' verdicts
# against the owner, by place). Records go to $W (not committed). Waits for litolff6.sh (one large gather at a time).
cd "$(dirname "$0")/../../.."
W=${W:-/private/tmp/s3work}
while ! grep -q "litolff6 on exit" benchmarks/page-ledger-2026-10/s3/litolff6.log 2>/dev/null; do sleep 20; done
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
B=$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
for plate in brahms litolff; do
  if [ $plate = litolff ]; then PDF=$L; PG=2,4; else PDF=$B; PG=4,5; fi
  OMR_PAGE_MARKS=1 OMR_PAGE_OWNER=1 python3 -m tools.omr.staged "$PDF" --pages $PG --dpi 600 --weights auto --route-weights \
    --cell-map $LIB/_shared-records/cell-maps --no-surya --out "$W/$plate.on.record.json" --musicxml "$W/$plate.on.musicxml" > "$W/$plate.on.log" 2>&1
  echo "$plate on exit $?"
done
