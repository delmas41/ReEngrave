"""2.306 r13 study, Q4: heads NEW stems and OLD does not -- why OLD has none. Is there an OLD stem row (cell finder) on NEW's stem at all?
  no row            OLD's FINDER never filed that stem (its size / edge / pair / owner filters, or the cell cut)
  a row, no touch   the finder's box stops short of the head's detector box (the JOIN needs the two boxes to touch)
  a row that touches   OLD narrowed between two stems (two_stems / unison) or took another
Also where the stem stands against the cell: within 0.8 sp of the cell's left/right edge (the finder's barline filter). Our own output.
Usage: bwhy.py"""
import json, collections
from common import *
for pl in ("lit", "bra"):
    D = load(pl)
    ups = cell_up(D)
    T = json.load(open(S + "/r13/%s.trace.json" % pl))
    B = [r for r in T if not r["old_stem"] and r["new_read"] and not r.get("not_real")]
    rows = collections.defaultdict(list)
    for sid, st in D["stems"].items():
        if st["reader"] == "cv_lines":
            b = stem_page_box(D, ups, sid)
            if b:
                rows[st["cell"]].append(b)
    c = collections.Counter()
    for r in B:
        nb, hb, sp = r["new_box"], r["head_box"], r["sp"]
        cell = cell_of(r["g"])
        cb = D["cellbox"].get(cell)
        tol = 0.12 * (hb[3] - hb[1])
        mine = [b for b in rows.get(cell, ()) if abs((b[0] + b[2]) / 2 - (nb[0] + nb[2]) / 2) <= max(3, 0.35 * sp) and min(b[3], nb[3]) - max(b[1], nb[1]) > 0]
        if not mine:
            xc = (nb[0] + nb[2]) / 2
            edge = cb is not None and (xc - cb[0] < 0.9 * sp or cb[2] - xc < 0.9 * sp)
            length = (nb[3] - nb[1]) / sp
            k = "no OLD stem row on NEW's stem" + (": the stem stands at the cell's edge (barline filter)" if edge else (": NEW's stem is shorter than 2 sp" if length < 2.0 else (": longer than 8 sp" if length > 8 else "")))
        elif not any(b[0] <= hb[2] + tol and b[2] >= hb[0] - tol and b[1] <= hb[3] + tol and b[3] >= hb[1] - tol for b in mine):
            k = "an OLD stem row is there but its box does not touch the head box"
        else:
            k = "an OLD stem row touches the head (OLD: %s)" % r["old_why"]
        c[k] += 1
    print(pl, "NEW stems, OLD none:", len(B))
    for k, v in c.most_common():
        print("  %4d  %s" % (v, k))
