#!/bin/zsh
# ROADMAP 2.313: three small gathers of Litolff on today's main (this lane's worktree): arcs ON (defaults), arcs OFF, and p11 alone (staff-name proof).
# Page 1 rides along as the CONTEXT page (staff names are printed on it only); pages 11 and 16 carry most of the 162 -> 191.
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a7cf7de2261fce1a9
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/313
LIB=/Users/seanjohnson/Desktop/ReEngrave/library
LIT=$LIB/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf
cd $W
export OMR_SURYA_KEEP_ALIVE=0 OMR_DETECTOR_CACHE=$LIB/_shared-records/detector-cache
export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
one() { NAME=$1; PAGES=$2; shift 2
  echo "$(date +%T) start $NAME" >> $S/progress.txt
  env "$@" python3 -u -m tools.omr.staged $LIT --pages $PAGES --dpi 600 --weights auto --route-weights --cell-map $LIB/_shared-records/cell-maps --progress --out $S/$NAME.record.json > $S/$NAME.log 2>&1
  echo "$(date +%T) done $NAME rc=$?" >> $S/progress.txt
}
one g-on 1,11,16 X=1
one g-off 1,11,16 OMR_PAGE_ARC_WRITE=0 OMR_ARC_MEETING_AT_HEAD=0
one g-p11 11 X=1
echo "$(date +%T) ALL DONE" >> $S/progress.txt
