#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6176a29b46debf58
D=out/print/2.322-claim-gaps
benchmarks/claim-once-gaps-2026-11/run_when_quiet.sh python3 -m tools.omr.staged.judged score /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261117-night.record.json --doc brahms --json $D/judged-brahms.json > $D/judged-brahms.txt 2>&1
benchmarks/claim-once-gaps-2026-11/run_when_quiet.sh python3 benchmarks/claim-once-gaps-2026-11/gaps_page.py brahms 0,4,5,8,12,14,19,25 $D/data > $D/gaps-brahms.log 2>&1
