#!/bin/bash
# ROADMAP 2.304: one page gather of one plate with the 2.303 probe (OCR text per candidate).
# usage: gather_plate.sh PLATE ARM PAGES   (flag env passed through; outputs in library/_shared-records/2304-work)
cd "$(dirname "$0")/../.."
PLATE=$1; ARM=$2; PAGES=$3
W=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/2304-work
mkdir -p $W
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/editions
if [ "$PLATE" = litolff ]; then PDF=$LIB/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf; else PDF=$LIB/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf; fi
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/detector-cache OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export PROBE_OUT=$W/$PLATE.$ARM.probe.json
python3 -u benchmarks/text-reader-owned-ink-2026-11/owned_probe.py "$PDF" --pages $PAGES --dpi 600 --weights auto --route-weights --out $W/$PLATE.$ARM.gathered.record.json > $W/$PLATE.$ARM.gather.log 2>&1
echo done $? >> $W/$PLATE.$ARM.gather.log
