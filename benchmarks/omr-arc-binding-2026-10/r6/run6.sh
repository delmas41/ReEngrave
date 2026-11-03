#!/bin/bash
# 2.252 r6: re-adjudicate the r6 gathers (this tree, both arms) at main's defaults, OMR_HEAD_HOLE_POSITION 0 vs 1, then lane_report.
# args: TAG SPECS...   spec = short:name:plate   e.g. l1011:litolff-p10-11:litolff
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a45c4f12e17f87776
T=$1; shift
G=out/2.252r6/g
R4=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf/out/2.252r4
O=out/2.252r6/$T; mkdir -p $O
export OMR_SURYA_KEEP_ALIVE=0
grep -c "crop abandoned" $G/*.log >> $O/done
for spec in "$@"; do
  IFS=: read s n p <<< "$spec"
  for a in off on; do
    if [ $a = on ]; then h=1; else h=0; fi
    OMR_HEAD_HOLE_POSITION=$h python3 benchmarks/hairpin-reach-2026-11/readjudicate.py $G/$n.$a.gathered.record.json $O/$n.$a.readj.record.json > $O/$n.$a.readj.log 2>&1
    echo "$n $a rc=$? $(date)" >> $O/done
  done
  LANE_REPORT_SAMPLE=$R4/sample-$s.json python3 benchmarks/omr-arc-binding-2026-10/report_saved_gathers_r4.py \
    --saved $p:off=$O/$n.off.readj.record.json --saved $p:on=$O/$n.on.readj.record.json -- \
    --from gather --plates $p --workers 2 --cell-map master --out $O/rep-$s \
    --flag OMR_HEAD_HOLE_POSITION=0:1 > $O/rep-$s.log 2>&1
  echo "rep $s rc=$? $(date)" >> $O/done
done
echo ALLDONE >> $O/done
