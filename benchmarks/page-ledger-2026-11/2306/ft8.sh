#!/bin/zsh
# 2306 r8: whole fast tier with OMR_PAGE_STEMS=1 in the real worktree (branch tip, retire commit active). Quiet; summary to ft8.done.
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a40f8a2f924e1d729
export OMR_PAGE_STEMS=1 OMR_SURYA_KEEP_ALIVE=0 OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
echo "start $(date +%T) $(git rev-parse --short HEAD)" >> $S/r6/ft8.done
python3 -m pytest -m "not slow" tools/omr/tests -q -p no:cacheprovider -rf --no-header > $S/r6/ft8.log 2>&1
echo "rc=$? $(date +%T)" >> $S/r6/ft8.done
tail -1 $S/r6/ft8.log >> $S/r6/ft8.done
grep "^FAILED" $S/r6/ft8.log >> $S/r6/ft8.done
echo ALL >> $S/r6/ft8.done
