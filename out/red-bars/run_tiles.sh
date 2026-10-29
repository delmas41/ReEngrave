#!/bin/bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a78f8f9c4e5bc261c
export OMR_SURYA_KEEP_ALIVE=0 PYTHONPATH=.
python3 out/red-bars/tiles.py
