#!/bin/sh
# 2.170: one Brahms record load at a time on the shared box -- wait until no other lane's Brahms replay runs, then replay OFF,ON
# under the record-load lock. Writes .s170/replay/brahms.log.
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-acb2d0a36e0483fc1 || exit 1
while pgrep -f "replay_2_165.py brahms" >/dev/null; do sleep 30; done
python3 benchmarks/omr-beams-shattered-2026-10/probe/replay_2_170.py brahms \
  /private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-d8bd32/c817424a-b1ff-47f2-86d2-bb8772841714/scratchpad/slices \
  .s170/replay off,on --lock > .s170/replay/brahms.log 2>&1
