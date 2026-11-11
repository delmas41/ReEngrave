#!/bin/bash
# Run the listed small gathers (2 pages each) one at a time, each only while fewer than 2 gathers (python -m tools.omr.staged <pdf>) are
# running on the machine ("one large gather at a time plus small 2-page checks beside it", CLAUDE.md lean lanes).
# usage: queue.sh "PLATE PAGES ARM [ENV=V...]" "PLATE PAGES ARM ..." ...
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a01cb0ffa95891123
for job in "$@"; do
  while [ "$(ps aux | grep -E 'tools\.omr\.staged /Users' | grep -v grep | wc -l)" -ge 2 ]; do sleep 20; done
  echo "$(date +%T) start $job"
  benchmarks/stems-rerun-2026-11/gather.sh $job > out/stems-rerun/$(echo $job | awk '{print $1"."$3}').log 2>&1
  echo "$(date +%T) done $job rc=$?"
done
