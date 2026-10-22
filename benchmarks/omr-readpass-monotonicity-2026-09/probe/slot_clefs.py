#!/usr/bin/env python3
"""What clef does each SLOT read, and what did the fit make of slot 8?

    slot_clefs.py ARM.json CLEFS.json
"""
from __future__ import annotations

import collections
import json
import sys

arm = json.load(open(sys.argv[1]))
blob = arm["contextual"]["absent_instrument_veto"]
print("slots 5-11:",
      [(s["slot"], s["instrument"], s.get("source"))
       for s in blob["slot_instruments"] if 5 <= s["slot"] <= 11])

slot = {(r["page_index"], r["system_index"], r["staff_index"]): r["slot"]
        for r in blob["staff_slots"]}
tally: dict[int, collections.Counter] = collections.defaultdict(
    collections.Counter)
for pg, sy, si, clef, _src in json.load(open(sys.argv[2]))["rows"]:
    s = slot.get((pg, sy, si))
    if s is not None and s >= 0:
        tally[s][clef] += 1
for s in sorted(tally):
    print(f"  slot {s:>3}: {dict(tally[s])}")
