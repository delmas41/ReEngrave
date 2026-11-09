#!/bin/bash
# gate.sh PLATE PAGE : the real staged gather + export, flag OFF then ON, the exported musicxml md5 of both
export OMR_SURYA_KEEP_ALIVE=0
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8389a3ec3b455850
LIB=/Users/seanjohnson/Desktop/ReEngrave/library/editions
case $1 in
  litolff) PDF=$LIB/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf;;
  brahms) PDF=$LIB/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf;;
esac
for arm in off on; do
  if [ $arm = on ]; then export OMR_PAGE_ARCS=1; else unset OMR_PAGE_ARCS; fi
  python3 -m tools.omr.staged "$PDF" --pages $2 --weights auto --route-weights --dpi 600 --detector-cache /tmp/r4/dcache --musicxml /tmp/r4/$1$2-$arm.musicxml --out /tmp/r4/$1$2-$arm.rec.json > /tmp/r4/$1$2-$arm.log 2>&1
  echo "$1 p$2 $arm exit $?"
  md5 -q /tmp/r4/$1$2-$arm.musicxml
done
