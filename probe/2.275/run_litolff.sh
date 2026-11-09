#!/bin/bash
# 2.275: Litolff, control (636ec4742 code) then current tree. usage: run_litolff.sh SCRATCH
S="$1"
export OMR_SURYA_KEEP_ALIVE=0
L=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/beethoven5-litolff-mvt1-whole-20261104-night.record.json
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abb46cd422dbf2aca
OMR_TREE="$S/ctl" python3 probe/2.275/p1_table.py "$L" "$S/out/lit_ctl" > "$S/out/lit_ctl.log" 2>&1
python3 probe/2.275/p1_table.py "$L" "$S/out/lit_now" > "$S/out/lit_now.log" 2>&1
echo done > "$S/out/lit.done"
