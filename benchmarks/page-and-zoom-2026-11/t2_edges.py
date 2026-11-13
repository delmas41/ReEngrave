"""ROADMAP 2.307 T1c/T2 -- where do the head/rest/accidental boxes that only ONE way finds sit relative to the cells? (measure only)

    python3 benchmarks/page-and-zoom-2026-11/t2_edges.py WORK_DIR

For every "only cells" box (cells find it, row / band do not) and every "only this way" box (row / band find it, cells do not), same merge
and same-family IoU >= 0.3 matching as `t2_score.py`: is its centre within 1 staff space of a cell's left/right edge (a barline or a system
end), within 1 staff space of a cell crop's top/bottom edge, or in the open? If cells lose marks at their edges, the "only this way" boxes
should crowd the edges more than the boxes every way finds.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_sys.path.insert(0, _os.path.dirname(__file__))

import collections
import glob
import json
import os
import sys

from t2_score import fam_boxes, iou, merged  # noqa: E402

FAMS = ("head_filled", "head_hollow", "head_whole", "rest", "accidental")


def where(b, cells, sp):
    cx, cy = (b[2] + b[4]) / 2, (b[3] + b[5]) / 2
    best = "outside every cell"
    for c in cells:
        x0, y0, x1, y1 = c
        if x0 <= cx <= x1 and y0 <= cy <= y1:
            if min(cx - x0, x1 - cx) <= sp:
                return "x-edge (barline)"
            if min(cy - y0, y1 - cy) <= sp:
                best = "y-edge (crop top/bottom)"
            elif best == "outside every cell":
                best = "open"
    return best


def main():
    work = sys.argv[1]
    tab = collections.defaultdict(collections.Counter)
    for f in sorted(glob.glob(os.path.join(work, "*.p*.json"))):
        d = json.load(open(f))
        sp = sorted(s["sp"] for s in d["staves"].values())[len(d["staves"]) // 2]
        cells = [it["bbox"] for it in d["ways"]["cells"]["items"]]
        ways = {w: fam_boxes(merged(d["ways"][w]["items"])) for w in ("cells", "row", "band")}
        for fam in FAMS:
            cb = ways["cells"].get(fam, [])
            for w in ("row", "band"):
                wb = ways[w].get(fam, [])
                for b in wb:
                    k = "both" if any(iou(b[2:], c[2:]) >= 0.3 for c in cb) else "only_" + w
                    tab["%s %s %s" % (d["plate"], w, k)][where(b, cells, sp)] += 1
                for c in cb:
                    if not any(iou(b[2:], c[2:]) >= 0.3 for b in wb):
                        tab["%s %s only_cells" % (d["plate"], w)][where(c, cells, sp)] += 1
    for k in sorted(tab):
        t = tab[k]
        n = sum(t.values())
        print("%-28s n %5d  " % (k, n) + "  ".join("%s %d (%.0f%%)" % (w, v, 100.0 * v / n) for w, v in sorted(t.items())))


if __name__ == "__main__":
    main()
