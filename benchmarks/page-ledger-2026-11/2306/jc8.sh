#!/bin/zsh
# 2306 r8: judged_claims on the r8 flag-ON slices against the base (main gathers of the same pages, the r4 baseline jsons)
S=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-project-mgmt-pipeline-review-e6581e/77ea0805-f478-4ed7-b4b6-89b2b63b5322/scratchpad
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a40f8a2f924e1d729
for pair in "lit-a:6,16" "lit-b:2,4,8" "lit-c:9,10,11"; do
  n=${pair%%:*}; p=${pair#*:}
  python3 -m tools.omr.staged.judged_claims $S/2306-slices8/litolff --doc litolff --pages $p --json $S/r6/jc8-on-$n.json --against $S/2306-jc-base-$n.json > $S/r6/jc8-on-$n.txt 2>&1
  echo "$n rc=$?" >> $S/r6/jc8.done
done
python3 -m tools.omr.staged.judged_claims $S/2306-slices8/brahms --doc brahms --pages 0,5 --json $S/r6/jc8-on-bra.json --against $S/2306-jc-base-bra.json > $S/r6/jc8-on-bra.txt 2>&1
echo "bra rc=$?" >> $S/r6/jc8.done
echo ALL >> $S/r6/jc8.done
