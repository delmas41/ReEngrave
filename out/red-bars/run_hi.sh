#!/bin/bash
# run_hi.sh PLATE PAGES glyph...
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
R=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather
plate=$1; pages=$2; shift 2
python3 out/red-bars/headinfo.py $R/$plate.record.json $pages "$@"
