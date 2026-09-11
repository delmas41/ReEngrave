"""How WIDE is a refused arc, in the page's own unit?

A slur or a tie is drawn between two noteheads, so the narrowest real one is
about as wide as the gap between two adjacent heads. An arc narrower than a
single notehead cannot bind two of them by construction -- so if the refused
population is mostly narrow, "the notes were never detected" is the wrong
story for it and the arc itself is the suspect.

⚠️ Measured in STAFF SPACES, not pixels, so the number means the same thing on
any print: the divisor is the staff's OWN spacing, which `_flatten_part`
already carries beside each bar.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads: "collections.Counter" = collections.Counter()
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = E._parse_subject(o["subject"])
        if s["glyph"] is None or not rec.obs(Q.NOTEHEAD_CLASS, o["subject"]):
            continue
        heads[(s["page"], s["system"], s["staff"], s["cell"] or 0)] += 1

    rows = []
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            sp = spacings[segments[0][0]] or 0
            total_w = sum(b[2] for _m, b in segments)
            rows.append({
                "bound": len(covered),
                "w_sp": (total_w / sp) if sp else None,
                "kind": ("tie" if "tie" in {kinds.get(id(b)) for _m, b in segments}
                         else "slur"),
                "bar_heads": sum(
                    heads.get((cells[m][0].page, cells[m][0].system,
                               cells[m][0].staff, cells[m][1]), 0)
                    for m, _b in segments),
            })

    def q(xs):
        xs = sorted(x for x in xs if x is not None)
        if not xs:
            return "n/a"
        return (f"n={len(xs)} p10={xs[len(xs)//10]:.2f} "
                f"med={statistics.median(xs):.2f} p90={xs[len(xs)*9//10]:.2f}")

    print("ARC WIDTH in STAFF SPACES")
    print("  binds >=2 :", q([r["w_sp"] for r in rows if r["bound"] >= 2]))
    print("  binds  1  :", q([r["w_sp"] for r in rows if r["bound"] == 1]))
    print("  binds  0  :", q([r["w_sp"] for r in rows if r["bound"] == 0]))
    print()
    b: "collections.Counter" = collections.Counter()
    for r in rows:
        k = "2+" if r["bound"] >= 2 else str(r["bound"])
        w = r["w_sp"]
        bucket = ("<1.0" if w < 1.0 else "1-2" if w < 2 else "2-3" if w < 3
                  else "3-5" if w < 5 else "5+")
        b[(bucket, k)] += 1
    print("width bucket x how many heads it binds")
    for bk in ["<1.0", "1-2", "2-3", "3-5", "5+"]:
        print(f"  {bk:5s}", {k: v for (bb, k), v in sorted(b.items()) if bb == bk})
    print()
    print("refused, in bars that DO hold gathered heads:",
          sum(1 for r in rows if r["bound"] < 2 and r["bar_heads"] > 0))
    print("refused, in bars with NO gathered head:",
          sum(1 for r in rows if r["bound"] < 2 and r["bar_heads"] == 0))


if __name__ == "__main__":
    main(sys.argv[1])
