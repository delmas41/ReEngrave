"""NAME the notes under a refused arc, one bar at a time.

⚠️ This project's own lesson, learned three times: *counting cannot see a
relocation; only naming the notes can* -- and the arc-export session's mutation
battery found a frame error that every span COUNT walked past. So before any
repair, print the arc's x-range and every gathered notehead x-centre in its
bar, with each head's fate, and read them.

Prints the largest refused groups first, because a wide arc over a bar holding
notes is the case no easy story explains.
"""
from __future__ import annotations

import collections
import json
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import head_fate, heads_by_cell  # noqa: E402


def main(path: str, want: int = 12) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)

    shown = 0
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            if len(covered) >= 2 or shown >= want:
                continue
            sp = spacings[segments[0][0]] or 1.0
            w = sum(b[2] for _m, b in segments) / sp
            if w < 4.0:
                continue          # a short arc is a different question
            kind = ("tie" if "tie" in {kinds.get(id(b)) for _m, b in segments}
                    else "slur")
            shown += 1
            print(f"\n=== {kind}  {w:.1f} staff spaces, {len(segments)} segment(s), "
                  f"binds {len(covered)} ===")
            for m_idx, (ax, _ay, aw, _ah) in segments:
                r_, c_ = cells[m_idx]
                key = (r_.page, r_.system, r_.staff, c_)
                pool = heads.get(key) or []
                bar = measures[m_idx].get("bbox_page_px")
                print(f"  p{r_.page}/s{r_.system}/st{r_.staff}/c{c_}  "
                      f"arc x {ax:.0f}..{ax+aw:.0f}"
                      + (f"   bar x {bar[0]:.0f}..{bar[2]:.0f}" if bar else
                         "   bar has NO page box"))
                if not pool:
                    print("      (no gathered notehead in this bar)")
                for h in sorted(pool, key=lambda h: (h["page_box"] or [1e9])[0]):
                    pb = h["page_box"]
                    if pb is None:
                        print(f"      {h['subject']:28s} NO PAGE BOX      "
                              f"{h['fate']}")
                        continue
                    xc = pb[0] + pb[2] / 2.0
                    inside = "IN " if ax <= xc <= ax + aw else "   "
                    print(f"      {h['subject']:28s} x {xc:7.0f} {inside} "
                          f"{h['fate']}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12)
