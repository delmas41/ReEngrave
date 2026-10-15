#!/bin/bash
# usage: gather.sh TAG PAGES [ENV=VAL ...]
cd "$(dirname "$0")/.."
TAG=$1; PG=$2; shift 2
PDF=library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
env "$@" nice -n 10 python3 -m tools.omr.staged $PDF --pages $PG --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt --through adjudicate --no-surya --no-ocr --out runs/$TAG.json > runs/$TAG.log 2>&1
echo done $? >> runs/$TAG.log
