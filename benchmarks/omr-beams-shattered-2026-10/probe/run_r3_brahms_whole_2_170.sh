#!/bin/sh
# 2.170 round 3: Brahms WHOLE movement, arms off,both -- after the p0-8 run ends and while no other lane's Brahms replay runs.
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-acb2d0a36e0483fc1 || exit 1
SL=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-d8bd32/c817424a-b1ff-47f2-86d2-bb8772841714/scratchpad/slices
until grep -q R3DONE .s170/r3/brahms.log 2>/dev/null; do sleep 30; done
while pgrep -f "replay_2_16[0-9].py brahms|replay_2_17[1-9].py brahms" >/dev/null; do sleep 30; done
mkdir -p .s170/r3w
python3 benchmarks/omr-beams-shattered-2026-10/probe/replay_2_170.py brahms $SL .s170/r3w off,both --lock > .s170/r3w/brahms.log 2>&1
