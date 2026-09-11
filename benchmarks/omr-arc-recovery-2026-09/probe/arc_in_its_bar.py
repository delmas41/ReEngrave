"""Is a refused arc even INSIDE the bar it was placed in?

`arc_widths.py` kills the easy story: an arc that binds zero heads is a median
**6.23 staff spaces** wide against a bound arc's 6.40, so the refused
population is not narrow junk ink -- these are full-length curves, in bars that
hold noteheads, covering none of them.

An arc that wide over a bar that has notes and touches none of them is a
placement question, not a reading one. `_place_arcs` sends an arc to the cell
its OWNER names but keeps the SUBJECT's cell INDEX -- and a cell index is a
per-staff segmentation ordinal, so staff 5's bar 7 and staff 9's bar 7 need not
be the same stretch of page. This asks the question directly, in page pixels:
does the arc's x-range overlap the x-range of the bar it landed in?

⚠️ x ONLY. `_noteheads_under` tests x only, so that is the comparison that
decides whether a head can be found; adding y here would measure something the
pairing never asks.
"""
from __future__ import annotations

import collections
import json
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)

    moved = same = 0
    for o in rec.obs_of(Q.ARC_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None:
            continue
        owner = rec.value(Q.ARC_OWNER, sub)
        home = E._staff_key(s["page"] or 0, s["system"] or 0, s["staff"] or 0)
        if isinstance(owner, str) and owner != home:
            moved += 1
        else:
            same += 1
    print(f"arc rows: owner == subject staff {same}, MOVED {moved}")

    buckets: "collections.Counter" = collections.Counter()
    examples = []
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            key = "binds_2+" if len(covered) >= 2 else f"binds_{len(covered)}"
            for m_idx, (ax, _ay, aw, _ah) in segments:
                bar = measures[m_idx].get("bbox_page_px")
                if not bar:
                    buckets[(key, "bar_has_no_box")] += 1
                    continue
                bx0, bx1 = float(bar[0]), float(bar[2])
                ox = max(0.0, min(bx1, ax + aw) - max(bx0, ax))
                frac = ox / aw if aw > 0 else 0.0
                lab = ("inside" if frac >= 0.9 else
                       "mostly" if frac >= 0.5 else
                       "partly" if frac > 0.0 else "OUTSIDE")
                buckets[(key, lab)] += 1
                if lab == "OUTSIDE" and len(examples) < 10:
                    r_, c_ = cells[m_idx]
                    examples.append(
                        f"p{r_.page}/s{r_.system}/st{r_.staff}/c{c_}: "
                        f"arc x {ax:.0f}..{ax+aw:.0f}  bar x {bx0:.0f}..{bx1:.0f}")

    print("\narc segment x-overlap with the bar it was PLACED in:")
    for k in sorted(buckets):
        print(f"  {k[0]:9s} {k[1]:15s} {buckets[k]}")
    print("\nOUTSIDE examples:")
    for e in examples:
        print("   ", e)


if __name__ == "__main__":
    main(sys.argv[1])
