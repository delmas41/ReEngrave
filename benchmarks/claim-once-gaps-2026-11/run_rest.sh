#!/bin/bash
# after run_brahms.sh (pid given as $1) ends: Brahms ink readout, then judged_claims on both plates, one at a time
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6176a29b46debf58
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=$PWD
D=out/print/2.322-claim-gaps
while kill -0 "$1" 2>/dev/null; do sleep 20; done
Q=benchmarks/claim-once-gaps-2026-11/run_when_quiet.sh
$Q python3 -m tools.omr.staged.claim_readout ink brahms:20261117-night --pages 0,4,5,8,12,14,19,25 --out $D/ink-brahms > $D/ink-brahms.txt 2>&1
$Q python3 -m tools.omr.staged.judged_claims litolff:20261117-night --doc litolff --pages 2,4,6,8,9,10,11,16 --json $D/jc-litolff.json > $D/jc-litolff.txt 2>&1
$Q python3 -m tools.omr.staged.judged_claims brahms:20261117-night --doc brahms --pages 0,4,5,8,12,14,19,25 --json $D/jc-brahms.json > $D/jc-brahms.txt 2>&1
echo done > $D/rest.done
