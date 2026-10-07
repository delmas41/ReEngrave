#!/bin/bash
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees
R=/Users/seanjohnson/Desktop/ReEngrave
O=$W/ab258-out
LIT=$R/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
BRA=$R/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
export OMR_DIRECTION_TEXT_SCAN_GATE=1 OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=$R/.venv-omrned/bin/python
run() { # arm tag pdf pages
  local arm=$1 tag=$2 pdf=$3 pages=$4
  local out=$O/$tag.$arm.json
  [ -s $out ] && return
  cd $W/ab258-$arm
  local t0=$(date +%s)
  python3 -m tools.omr.staged "$pdf" --pages $pages --weights auto --through adjudicate --out $out > $O/$tag.$arm.log 2>&1
  echo "$tag $arm rc=$? wall=$(( $(date +%s)-t0 ))" >> $O/times.txt
}
for spec in "lit6|$LIT|6" "lit6B|$LIT|6|baseonly" "lit12|$LIT|12" "lit1-3|$LIT|1-3" "bra7|$BRA|7" "bra0-1|$BRA|0-1"; do
  IFS='|' read tag pdf pages only <<< "$spec"
  run base $tag "$pdf" $pages
  [ -n "$only" ] && continue
  run arm $tag "$pdf" $pages
done
echo ALLDONE >> $O/times.txt
