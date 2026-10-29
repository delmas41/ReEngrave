#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
mkdir -p out/red-bars/work
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
R=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.222-one-head/out/lane-report/2.222-gather
python3 out/print/2.229-ranking/export_saved.py $R/litolff.record.json out/red-bars/work litolff 1,2,4,6,8,9,10,11,16 new > out/red-bars/work/lit.log 2>&1
python3 out/print/2.229-ranking/export_saved.py $R/brahms.record.json out/red-bars/work brahms 0,4,5,8,12,14,19,25 new > out/red-bars/work/bra.log 2>&1
echo done > out/red-bars/work/done
