#!/bin/sh
# 2.180: slice both night records (one at a time), then replay ADJUDICATE..EXPORT off vs on. Unattended (nohup).
# usage: sh run_replay.sh DATADIR   (from the worktree root)
D="$1"
python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/pages_2_165.py litolff $D/slices
python3 benchmarks/omr-augmentation-dots-2026-10/probe/replay_2_180.py litolff $D/slices $D/replay off,on
python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/pages_2_165.py brahms $D/slices
python3 benchmarks/omr-augmentation-dots-2026-10/probe/replay_2_180.py brahms $D/slices $D/replay off,on
echo REPLAY_DONE
