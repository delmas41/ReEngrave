#!/bin/sh
# ONE run for the six crops (same seed, same bars): Litolff x3 then Brahms x3 into out/print/2.173/
L=/Users/seanjohnson/Desktop/ReEngrave/library
rm -f out/print/2.173/*.png out/print/2.173/manifest.*.json
python3 benchmarks/omr-red-bars-2026-10/crops.py $L/_shared-records/beethoven5-litolff-mvt1-whole-20261018-night.record.json $L/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf out/print/2.173 litolff 1 1 1
python3 benchmarks/omr-red-bars-2026-10/crops.py $L/_shared-records/brahms1-breitkopf-mvt1-whole-20261018-night.record.json $L/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf out/print/2.173 brahms 1 1 1
