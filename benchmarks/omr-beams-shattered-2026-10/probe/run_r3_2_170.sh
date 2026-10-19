#!/bin/sh
# 2.170 round 3 (the two additions): Litolff whole movement, then Brahms pages 0-8, four arms each, serial (one load at a time).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-acb2d0a36e0483fc1 || exit 1
SL=/private/tmp/claude-501/-Users-seanjohnson-Desktop-ReEngrave--claude-worktrees-start-here-go-d8bd32/c817424a-b1ff-47f2-86d2-bb8772841714/scratchpad/slices
mkdir -p .s170/r3
python3 benchmarks/omr-beams-shattered-2026-10/probe/replay_2_170.py litolff $SL .s170/r3 off,tip,arc,both > .s170/r3/litolff.log 2>&1
python3 benchmarks/omr-beams-shattered-2026-10/probe/replay_2_170.py brahms .s170/sub .s170/r3 off,tip,arc,both > .s170/r3/brahms.log 2>&1
echo R3DONE >> .s170/r3/brahms.log
