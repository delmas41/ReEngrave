#!/bin/zsh
# 2.305 r9: one Brahms page gather on the lane tree (merged main), both arc flags ON so the Q.PAGE_ARC rows exist;
# the OFF/ON and before/after arms are re-adjudicated from this one gather (replay.py).
# usage: NAME=g0 PAGES=0 gather.sh
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a74f60b633a6bef05
S=${R9_OUT:-/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/r9}
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
BRA=$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
mkdir -p $S
cd $W
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
export OMR_PAGE_ARC_WRITE=1 OMR_ARC_MEETING_AT_HEAD=1
N=${NAME:-g0}
echo "$(date +%T) start $N $(git rev-parse --short HEAD)" >> $S/progress.txt
python3 -u -m tools.omr.staged $BRA --pages ${PAGES:-0} --dpi 600 --weights auto --route-weights --cell-map $LIB/_shared-records/cell-maps --progress --out $S/$N.record.json > $S/$N.log 2>&1
echo "$(date +%T) done $N rc=$?" >> $S/progress.txt
