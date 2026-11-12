#!/bin/bash
# ROADMAP 2.290 build: `claim_readout ink` on the measure's own gathers, OFF rows with the flags 0 and ON rows with the flags 1 (the readout re-runs
# the stroke owner with the env it is given), per plate; and `judged_claims` ON against the OFF arm's json. One process at a time.
cd "$(dirname "$0")/../.."
D=${1:-out/m290}
for p in litolff brahms; do
  pg=2,8,11; [ $p = brahms ] && pg=14,19
  python3 -m tools.omr.staged.claim_readout ink $D/b290-$p-off.record.json --pages $pg > $D/ink-$p-off.txt 2>&1
  OMR_PAGE_HEAD_ONE=1 OMR_PAGE_HEAD_LEDGER=1 python3 -m tools.omr.staged.claim_readout ink $D/b290-$p-on.record.json --pages $pg > $D/ink-$p-on.txt 2>&1
  python3 -m tools.omr.staged.judged_claims $D/b290-$p-off.record.json --doc $p --json $D/jc-$p-off.json > $D/jc-$p-off.txt 2>&1
  OMR_PAGE_HEAD_ONE=1 OMR_PAGE_HEAD_LEDGER=1 python3 -m tools.omr.staged.judged_claims $D/b290-$p-on.record.json --doc $p --against $D/jc-$p-off.json --json $D/jc-$p-on.json > $D/jc-$p-on.txt 2>&1
done
echo done > $D/readouts.done
