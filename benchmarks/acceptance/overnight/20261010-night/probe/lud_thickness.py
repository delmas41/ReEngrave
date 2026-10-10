#!/usr/bin/env python3
"""lud_thickness: how thick are the strokes the 2.74 ink reader measured, against its cut?

`Q.BEAM_STROKE_INK` rows (observations; never pooled) carry `thickness_ratio` = median stroke thickness in
staff-line thicknesses. rhythm.py refuses a stroke below BEAM_THICKNESS_RATIO_MIN (1.75). A histogram says
whether the refused strokes sit far under the cut (a hairpin's or slur's line) or crowd it (a thin real beam on
a light plate). Streamed with ijson over the unpooled observations only (see lud_extract.py's docstring).
"""
import collections
import sys

import ijson

doc, path = sys.argv[1], sys.argv[2]
CUT = 1.75
vals = []
n = 0
with open(path, "rb") as fh:
    for o in ijson.items(fh, "record.observations.item", use_float=True):
        if o["quantity"] != "beam_stroke_ink":
            continue
        n += 1
        r = (o.get("detail") or {}).get("thickness_ratio")
        if r is not None:
            vals.append(float(r))
vals.sort()
print(f"{doc}: {n} Q.BEAM_STROKE_INK rows, {len(vals)} with a thickness_ratio")
edges = [0, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 6.0, 1e9]
h = collections.Counter()
for v in vals:
    for a, b in zip(edges, edges[1:]):
        if a <= v < b:
            h[(a, b)] += 1
            break
for (a, b), c in sorted(h.items()):
    mark = "  <-- below the cut: refused as too_thin" if b <= CUT else ""
    print(f"  {a:>4} .. {('inf' if b > 1e8 else b):<5} {c:6d} {'#' * int(60 * c / max(h.values()))}{mark}")
below = sum(1 for v in vals if v < CUT)
print(f"  below {CUT}: {below} ({100 * below / len(vals):.0f}%); between 1.5 and 1.75: {sum(1 for v in vals if 1.5 <= v < CUT)}; "
      f"between 1.75 and 2.0: {sum(1 for v in vals if CUT <= v < 2.0)}")
