#!/bin/bash
# mk.sh PLATE KIND key key ...   -> crops into out/red-bars/crops/PLATE
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
plate=$1; kind=$2; shift 2
python3 out/print/2.229-ranking/crop.py $plate out/red-bars/slice out/red-bars/crops/$plate $kind "$@"
