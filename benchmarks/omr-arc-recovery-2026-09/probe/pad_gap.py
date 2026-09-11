"""How far outside an arc's ink does the head it binds actually sit?

The crop settles what the counting could not: `REFUSED-slur-p2s1st0c10` is a
PRINTED SLUR over two chords, and it binds nothing. Its left chord's head
centre is at page x 1972 and its ink starts at 1980 -- eight pixels.
`_noteheads_under` pads by `_SLUR_ARC_PAD_NOTEHEADS` = **0.25 notehead
widths**, measured on the *engraved* Brahms fixture where *"of the 75 notehead
centres lying just outside an arc, 54 sit within 0.19 notehead widths of its
edge and the next is at 0.32"*.

⚠️ THIS DOES NOT PROPOSE MOVING THAT CONSTANT. It re-runs the measurement it
came from, on THIS document, and prints the distribution so a reader can see
whether the Brahms gap exists here at all. A constant read off a gap on one
print is only a constant while the gap is there.

The quantity is the same one: signed distance from the arc's edge to the
nearest notehead centre OUTSIDE it, in notehead widths, per end of each merged
arc. Only ends whose nearest outside head is in the arc's OWN bar are counted
-- a head in the next bar is a different question (see FINDINGS §4).
"""
from __future__ import annotations

import collections
import json
import statistics
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import heads_by_cell  # noqa: E402


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)

    gaps = []
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            # LEFT end of the leftmost segment, RIGHT end of the rightmost.
            lm, lb = segments[0]
            rm, rb = segments[-1]
            for m_idx, edge, side in ((lm, lb[0], "left"),
                                      (rm, rb[0] + rb[2], "right")):
                r_, c_ = cells[m_idx]
                pool = [h for h in
                        (heads.get((r_.page, r_.system, r_.staff, c_)) or [])
                        if h["page_box"]]
                if not pool:
                    continue
                w = sum(h["page_box"][2] for h in pool) / len(pool)
                outside = []
                for h in pool:
                    pb = h["page_box"]
                    xc = pb[0] + pb[2] / 2.0
                    d = (edge - xc) if side == "left" else (xc - edge)
                    if d > 0:
                        outside.append(d / w)
                if outside:
                    gaps.append(min(outside))

    gaps.sort()
    print(f"n ends with a head just outside: {len(gaps)}")
    print(f"  median {statistics.median(gaps):.3f} notehead widths")
    hist: "collections.Counter" = collections.Counter()
    for g in gaps:
        hist[round(min(g, 3.0) * 4) / 4] += 1
    print("\n  gap (notehead widths) -> count   [pad in force = "
          f"{_legacy._SLUR_ARC_PAD_NOTEHEADS}]")
    for k in sorted(hist):
        bar = "#" * min(60, hist[k])
        mark = "  <- inside the pad" if k <= _legacy._SLUR_ARC_PAD_NOTEHEADS else ""
        print(f"   {k:5.2f} {hist[k]:4d} {bar}{mark}")
    inside = sum(v for k, v in hist.items()
                 if k <= _legacy._SLUR_ARC_PAD_NOTEHEADS)
    print(f"\n  reached by the current pad: {inside} of {len(gaps)}")
    for cand in (0.5, 0.75, 1.0, 1.5):
        print(f"  a pad of {cand:4.2f} would reach: "
              f"{sum(1 for g in gaps if g <= cand)}")


if __name__ == "__main__":
    main(sys.argv[1])
