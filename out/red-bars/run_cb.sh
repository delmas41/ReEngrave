#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
R=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather
python3 out/red-bars/cellbox.py $R/litolff.record.json litolff
python3 out/red-bars/cellbox.py $R/brahms.record.json brahms
