#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
R=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather
python3 out/red-bars/farrate.py $R/litolff.record.json litolff 1,2,4,6,8,9,10,11,16
python3 out/red-bars/farrate.py $R/brahms.record.json brahms 0,4,5,8,12,14,19,25
