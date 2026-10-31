#!/bin/sh
# ROADMAP 2.240 step 2 (a) byte identity: OFF vs ON (OMR_PAGE_MARKS + OMR_PAGE_OWNER), OCR held fixed (--no-surya), master cells,
# shared detector cache, one gather at a time. Writes MusicXML + records under $W and prints cmp per plate.
cd "$(dirname "$0")/../../.."
W=${W:-/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-2.240-s2}
mkdir -p "$W"
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
B=$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
for plate in litolff brahms; do
  if [ $plate = litolff ]; then PDF=$L; PG=2,4; else PDF=$B; PG=4,5; fi
  for arm in off on; do
    if [ $arm = on ]; then V=1; else V=0; fi
    OMR_PAGE_MARKS=$V OMR_PAGE_OWNER=$V python3 -m tools.omr.staged "$PDF" --pages $PG --dpi 600 --weights auto --route-weights \
      --cell-map $LIB/_shared-records/cell-maps --no-surya --out "$W/$plate.$arm.record.json" --musicxml "$W/$plate.$arm.musicxml" \
      > "$W/$plate.$arm.log" 2>&1
    echo "$plate $arm exit $?"
  done
  if cmp -s "$W/$plate.off.musicxml" "$W/$plate.on.musicxml"; then echo "$plate MusicXML BYTE-IDENTICAL"; else echo "$plate MusicXML DIFFERS"; fi
done
