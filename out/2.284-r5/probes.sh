#!/bin/zsh
# 2.284 r5: cross-cell disagreement (both arms, both plates) and the Brahms p0 claim readout, on the fresh lane-report gathers.
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a86a05bfc6fca6a28
export OMR_SURYA_KEEP_ALIVE=0
W=out/2.284-r5/lane-report/work
O=out/2.284-r5
for arm in on off; do
  v=0; [ $arm = on ] && v=1
  for plate in brahms litolff; do
    python3 benchmarks/page-ledger-owns-2026-11/disagree_probe.py $W/$plate.$arm.gathered.record.json --env OMR_PAGE_LEDGER_OWNS=$v \
      --out $O/$plate.$arm.disagree.json > $O/$plate.$arm.disagree.txt 2>&1
  done
  python3 -m tools.omr.staged.claim_readout $W/brahms.$arm.gathered.record.json --truth auto --env OMR_PAGE_LEDGER_OWNS=$v \
    --out $O/readout-$arm-brahms > $O/readout-$arm-brahms.txt 2>&1
done
echo DONE > $O/probes.done
