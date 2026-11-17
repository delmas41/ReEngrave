#!/bin/zsh
# ROADMAP 2.313: for one saved gather G (g-on / g-off / g-p11) build the arms:
#   main     = the gather's own record, exported on today's main (r14 rules ON)
#   readj    = the same gather re-adjudicated on today's main (the control: must equal `main`)
#   nor14    = the same gather re-adjudicated + exported on main with the two r14 commits reverse-applied (r14 rules OFF)
# usage: [PLATE=brahms] arms.sh G PAGES_COUNTED  (arc flags for an arcs-OFF gather go in the environment of the caller)
G=$1; PAGES=$2
B=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/313
MAIN=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a7cf7de2261fce1a9
NOR=$B/tree-nor14
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
for T in main nor14; do
  if [ $T = main ]; then cd $MAIN; else cd $NOR; fi
  if [ $T = nor14 ]; then SRC=$B/$G.record.json; else SRC=$B/$G.record.json; fi
  python3 $MAIN/benchmarks/landing-check-2026-11/readj.py $SRC $B/$G.$T.readj.record.json
  python3 benchmarks/note-loss-funnel-2026-11/extract.py $B/$G.$T.readj.record.json $B/$G.$T.readj.facts.json
  mkdir -p $B/arms/$G-$T
  python3 -m tools.omr.staged.lane_report arm --tag 20261029-night --work $B/arms/$G-$T --from gather --plate ${PLATE:-litolff} --arm $G-$T --pages $PAGES --gathered $B/$G.$T.readj.record.json
done
cd $MAIN
python3 benchmarks/note-loss-funnel-2026-11/extract.py $B/$G.record.json $B/$G.orig.facts.json
mkdir -p $B/arms/$G-orig
python3 -m tools.omr.staged.lane_report arm --tag 20261029-night --work $B/arms/$G-orig --from gather --plate ${PLATE:-litolff} --arm $G-orig --pages $PAGES --gathered $B/$G.record.json
echo "$G arms done"
