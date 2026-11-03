#!/bin/bash
# 2.252 r6: 2-page gathers on THIS tree, one at a time, both arms (OFF = OMR_HEAD_HOLE_POSITION=0; ON = 1, r4+r5+r6 revisions).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a45c4f12e17f87776
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/detector-cache
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
B=$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
CM=$LIB/_shared-records/cell-maps
O=out/2.252r6/g
mkdir -p $O
for spec in litolff-p10-11:L:10,11:on litolff-p2-3:L:2,3:on litolff-p10-11:L:10,11:off litolff-p2-3:L:2,3:off brahms-p0-5:B:0,5:on brahms-p0-5:B:0,5:off; do
  IFS=: read name which pg arm <<< "$spec"
  if [ "$which" = L ]; then pdf=$L; else pdf=$B; fi
  if [ "$arm" = on ]; then hole=1; else hole=0; fi
  out=$O/$name.$arm.gathered.record.json
  [ -f "$out" ] && continue
  OMR_HEAD_HOLE_POSITION=$hole python3 -u -m tools.omr.staged "$pdf" --pages "$pg" --dpi 600 --weights auto --route-weights --cell-map "$CM" --out "$out" > $O/$name.$arm.log 2>&1
  echo "$name $arm rc=$? $(date)" >> $O/gather.done
done
echo ALLDONE >> $O/gather.done
