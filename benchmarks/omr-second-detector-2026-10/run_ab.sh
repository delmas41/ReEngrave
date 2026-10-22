#!/usr/bin/env bash
# ROADMAP 2.114 gather: Litolff 984073 pdf idx 1 and Brahms 317803 pdf idx 0, `--through adjudicate --no-surya --no-ocr` (2.110's command), the
# SAME clean committed tree, the SAME production weights, flag OFF vs ON (OMR_SECOND_HOLLOW_DETECTOR=1). One page at a time, nice 10.
# usage: run_ab.sh off|on [lit|bra ...]      records -> runs/2.114/ab/rec-<tag>-<arm>.json   (gitignored; FINDINGS carries the numbers)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
ARM="$1"; shift
TAGS="${*:-lit bra}"
E=/Users/seanjohnson/Desktop/ReEngrave/library/editions
LIT=$E/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRA=$E/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
W=omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt
OUT=runs/2.114/ab; mkdir -p "$OUT"
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then echo "DIRTY TREE -- an A/B on a dirty record is not a result"; exit 2; fi
LOCK=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/.gather-2.114.lock
trap 'rm -f "$LOCK"' EXIT INT TERM
echo "2.114 gather pid $$ $(date -u +%FT%TZ)" > "$LOCK"
for tag in $TAGS; do
  case $tag in lit) pdf=$LIT; pg=1;; bra) pdf=$BRA; pg=0;; esac
  avail=$(df -k /Users/seanjohnson/Desktop | awk 'NR==2{print int($4/1048576)}')
  [ "$avail" -lt 2 ] && { echo "STOP: under 2 GB free"; exit 3; }
  [ -s "$OUT/rec-$tag-$ARM.json" ] && { echo "have $tag $ARM"; continue; }
  echo "=== $ARM $tag p$pg ($(date +%T)) HEAD $(git rev-parse --short HEAD)"
  if [ "$ARM" = on ]; then export OMR_SECOND_HOLLOW_DETECTOR=1; else unset OMR_SECOND_HOLLOW_DETECTOR; fi
  nice -n 10 python3 -m tools.omr.staged "$pdf" --pages "$pg" --weights "$W" --through adjudicate --no-surya --no-ocr \
      --out "$OUT/rec-$tag-$ARM.json" >/dev/null 2>"$OUT/log-$tag-$ARM.txt"
done
