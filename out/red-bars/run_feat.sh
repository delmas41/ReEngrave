#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
R=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather
python3 out/red-bars/feat.py $R/litolff.record.json out/red-bars/work/litolff.feat.json litolff 1,2,4,6,8,9,10,11,16 > out/red-bars/work/lit.feat.log 2>&1
python3 out/red-bars/feat.py $R/brahms.record.json out/red-bars/work/brahms.feat.json brahms 0,4,5,8,12,14,19,25 > out/red-bars/work/bra.feat.log 2>&1
echo done > out/red-bars/work/feat.done
