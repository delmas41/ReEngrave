#!/bin/bash
# 2.255 r2: re-read the far-head ledger rows on the 20261029-night slices; OFF control, then ON (r1+r2 code).
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a37eb51cd656cda0a
export PYTHONPATH=$PWD OMR_SURYA_KEEP_ALIVE=0 OWNER=1 POOL_JSON=$PWD/out/2.255/pool_L.json OMR_FARHEAD_UNREAD_GUESSED=1
T=${TAG:-r2}
R=benchmarks/ledger-read-2026-11/reread.py
python3 $R litolff out/2.255/L_off_$T.json > out/2.255/L_off_$T.log 2>&1
OMR_LEDGER_READ=1 python3 $R litolff out/2.255/L_on_$T.json > out/2.255/L_on_$T.log 2>&1
unset POOL_JSON
python3 $R brahms out/2.255/B_off_$T.json > out/2.255/B_off_$T.log 2>&1
OMR_LEDGER_READ=1 python3 $R brahms out/2.255/B_on_$T.json > out/2.255/B_on_$T.log 2>&1
echo done > out/2.255/r2_done_$T
