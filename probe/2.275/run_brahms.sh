#!/bin/bash
# 2.275: Brahms, current tree, slim load, ALONE. usage: run_brahms.sh OUTDIR
export OMR_SURYA_KEEP_ALIVE=0
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-abb46cd422dbf2aca
python3 probe/2.275/p1_table.py /Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/brahms1-breitkopf-mvt1-whole-20261104-night.record.json "$1/bra_now" slim > "$1/bra_now.log" 2>&1
echo done > "$1/bra.done"
