"""Median notehead y-centre per cell — the HUGS arm's own input, kept apart.

⚠️ IT IS A SEPARATE FILE BECAUSE IT NEEDS THE 132 MB RECORD AND THE CONTROL
DOES NOT. `s6_control.py` runs off `reach.py`'s small output; making it load
the record too would put two readers of one file in one arm for no reason.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict

from tools.omr.staged import export as E
from tools.omr.staged.record import Kind, Q, Subject

rec = E.Record(json.load(open(sys.argv[1])))
by_cell = defaultdict(list)
for o in rec.obs_of(Q.GLYPH_BOX):
    if (o.get("detail") or {}).get("category") != "notehead":
        continue
    v = o["value"]
    if not isinstance(v, (list, tuple)) or len(v) < 5:
        continue
    cell = Subject.from_key(o["subject"]).at(Kind.CELL).to_key()
    by_cell[cell].append(float(v[2]) + float(v[4]) / 2.0)

json.dump({c: statistics.median(v) for c, v in by_cell.items()},
          open(sys.argv[2], "w"))
print(f"cells with noteheads: {len(by_cell)}")
