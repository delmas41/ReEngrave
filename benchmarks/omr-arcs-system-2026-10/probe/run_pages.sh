#!/bin/sh
# ROADMAP 2.166 -- the page A/Bs, one page at a time, serially (lean lanes). Writes out/2.166/ab_<doc>_p<page>.json.
cd "$(dirname "$0")/../../.."
export AB_RECORDS=1
for dp in "$@"; do
  doc=${dp%:*}; pg=${dp#*:}
  while pgrep -f "tools.omr.staged|page_ab.py .* out/2.166/ab_x" >/dev/null 2>&1 && pgrep -f "python.*-m tools.omr.staged " >/dev/null 2>&1; do sleep 30; done
  python3 benchmarks/omr-arcs-system-2026-10/probe/page_ab.py "$doc" "$pg" "out/2.166/ab_${doc}_p${pg}.json" > "out/2.166/ab_${doc}_p${pg}.log" 2>&1
  tail -1 "out/2.166/ab_${doc}_p${pg}.log"
done
echo ALLDONE
