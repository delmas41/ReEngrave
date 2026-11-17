#!/bin/zsh
# ROADMAP 2.313: Brahms p0 (Sean's judged page; also the plate's opening page) gathered on today's main, arcs ON (defaults) and arcs OFF.
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a7cf7de2261fce1a9
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/313
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
BRA=$LIB/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf
cd $W
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
one() { NAME=$1; PAGES=$2; shift 2
  echo "$(date +%T) start $NAME" >> $S/progress.txt
  env "$@" python3 -u -m tools.omr.staged $BRA --pages $PAGES --dpi 600 --weights auto --route-weights --cell-map $LIB/_shared-records/cell-maps --progress --out $S/$NAME.record.json > $S/$NAME.log 2>&1
  echo "$(date +%T) done $NAME rc=$?" >> $S/progress.txt
}
one b-on 0 X=1
one b-off 0 OMR_PAGE_ARC_WRITE=0 OMR_ARC_MEETING_AT_HEAD=0
echo "$(date +%T) BRAHMS DONE" >> $S/progress.txt
