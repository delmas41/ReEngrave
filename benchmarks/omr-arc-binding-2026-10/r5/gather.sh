#!/bin/bash
# 2.252 r5: Litolff 2-page gathers on this tree, one at a time. OFF = r4 flags off; ON = OMR_HEAD_HOLE_POSITION=1 (r4 + r5 revisions).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf
export OMR_UNISON_TIE_VOICE=1 OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/detector-cache
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
L=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
CM=$LIB/_shared-records/cell-maps
for spec in litolff-p10-11:10,11:on litolff-p2-3:2,3:on litolff-p10-11:10,11:off litolff-p2-3:2,3:off; do
  IFS=: read name pg arm <<< "$spec"
  out=out/2.252r5/$name.$arm.gathered.record.json
  [ -f "$out" ] && continue
  if [ "$arm" = on ]; then hole=1; else hole=0; fi
  OMR_HEAD_HOLE_POSITION=$hole python3 -u -m tools.omr.staged "$L" --pages "$pg" --dpi 600 --weights auto --route-weights --cell-map "$CM" --out "$out" > out/2.252r5/$name.$arm.log 2>&1
  echo "$name $arm rc=$? $(date)" >> out/2.252r5/gather.done
done
echo ALLDONE >> out/2.252r5/gather.done
