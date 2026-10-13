#!/bin/bash
# probe the 2.98 arm (main f5f43143) and diff it against the 7eec1bd9 arm; quiet output
P=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/held-out-2101
W=/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees
B=$W/agent-a8a7c1ba223215d9e/benchmarks/omr-held-out-2026-10
cd $W/held-out-main2
for d in dvorak8-novello:dvorak8 schumann2-peters:schumann2 tchaikovsky4-jurgenson:tchaikovsky4; do
  python3 $B/probe_reach.py $P/${d%%:*}-arm2.record.json $P/probe/${d##*:}-arm2.json > /dev/null 2>&1
  echo "== ${d%%:*}"
  python3 $B/compare.py $P/probe/${d##*:}-arm.json $P/probe/${d##*:}-arm2.json 2>&1 \
    | grep -E "^(notes_reaching|bars_held|held_note|bars_add_up)|measure_rest|whole|  rests |  notes |bar_does_not|overfull" | cut -c1-210
done
