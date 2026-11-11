#!/bin/bash
# usage: gather_one.sh PLATE PAGE ARM(on|off)
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a2250573c52066018
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad/lane290
R=/Users/seanjohnson/Desktop/ReEngrave/library
PLATE=$1; PG=$2; ARM=$3
if [ "$PLATE" = litolff ]; then PDF=$R/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf; else PDF=$R/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf; fi
V=0; [ "$ARM" = on ] && V=1
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$R/_shared-records/detector-cache OMR_PAGE_HEADS=$V OMR_PAGE_HEAD_VIEWS=$V OMR_PAGE_HEAD_CLAIM=$V
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
mkdir -p $S/g
( time python3 -u -m tools.omr.staged $PDF --pages $PG --dpi 600 --weights auto --route-weights --cell-map $R/_shared-records/cell-maps --through adjudicate --progress --out $S/g/$PLATE.p$PG.$ARM.record.json ) > $S/g/$PLATE.p$PG.$ARM.log 2>&1
echo done >> $S/g/$PLATE.p$PG.$ARM.log
