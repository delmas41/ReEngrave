#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6176a29b46debf58
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=$PWD
O=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/project-mgmt-pipeline-review-e6581e/out/print/2.322-claimed-twice
mkdir -p $O
Q=benchmarks/claim-once-gaps-2026-11/run_when_quiet.sh
$Q python3 benchmarks/claim-once-gaps-2026-11/cut_twice.py litolff 2,4,6,8,9,10,11,16 $O > $O/log_litolff.txt 2>&1
$Q python3 benchmarks/claim-once-gaps-2026-11/cut_twice.py brahms 0,4,5,8,12,14,19,25 $O > $O/log_brahms.txt 2>&1
echo done > $O/done
