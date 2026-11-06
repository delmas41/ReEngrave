"""BARLINE CUT TEST (measure only). Reads the saved 20261104-night GATHER slices of the frozen sample pages.

    python3 cut.py PLATE OUT.json

Per arc box: is its left/right end within 1 sp of its own cell's edge (a cell is cut barline to barline: no horizontal pad) and of any barline of
its system; against chance (the same box slid to a random x inside its cell, 200 draws). Edge pairs (right-cut box + left-cut box in the next cell
at the same height) = a barline-crossing arc boxed in two pieces; a lone cut box = the other half never boxed. Boxes with no page curve row.
"""
import collections
import json
import pathlib
import random
import sys

SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/%s.jsonl"
SAMPLE = {"litolff": [2, 4, 6, 8, 9, 10, 11, 16], "brahms": [0, 4, 5, 8, 12, 14, 19, 25]}
TOL = 1.0     # spaces


def pg(k):
    return int(k.split("/")[1])


def main():
    plate, out = sys.argv[1], sys.argv[2]
    pages = set(SAMPLE[plate])
    cell_box, arcs, curves, lines, heads = {}, {}, {}, {}, collections.defaultdict(list)
    piece_curve = {}
    for l in open(SL % (plate, "observations")):
        o = json.loads(l)
        q = o["quantity"]
        if q not in ("cell_box", "arc_box", "system_arc", "staff_lines", "glyph_box"):
            continue
        s = o["subject"]
        if pg(s) not in pages:
            continue
        if q == "cell_box":
            cell_box[s] = o["value"]
        elif q == "staff_lines":
            v = o["value"]
            lines[s] = (v[-1] - v[0]) / (len(v) - 1)
        elif q == "arc_box":
            arcs[s] = dict(cls=o["value"], box=o["detail"]["bbox_page_px"], score=o["score"])
        elif q == "system_arc":
            curves[s] = o
            for p in o["detail"].get("pieces") or ():
                piece_curve[p] = s
        elif q == "glyph_box" and (o["detail"] or {}).get("category") == "notehead":
            b = o["detail"].get("bbox_page_px")
            if b:
                heads["/".join(s.split("/")[1:4])].append(b)
    absn = {}
    for l in open(SL % (plate, "abstentions")):
        o = json.loads(l)
        if o["quantity"] == "system_arc" and pg(o["subject"]) in pages:
            absn[o["subject"]] = o.get("reason")
    # barlines per system = every cell edge of every staff of the system
    sys_edges = collections.defaultdict(set)
    staff_cells = collections.defaultdict(dict)
    for ck, b in cell_box.items():
        _, p, sy, st, m = ck.split("/")
        sys_edges[(p, sy)].update([b[0], b[2]])
        staff_cells[(p, sy, st)][int(m)] = b
    # adjacency check: do neighbouring cells of a staff abut?
    gaps = []
    for k, cs in staff_cells.items():
        for m, b in cs.items():
            if m + 1 in cs:
                gaps.append(cs[m + 1][0] - b[2])
    rows = []
    rng = random.Random(7)
    for ak, a in arcs.items():
        _, p, sy, st, m, gi = ak.split("/")
        cb = cell_box.get("cell/%s/%s/%s/%s" % (p, sy, st, m))
        sp = lines.get("staff/%s/%s/%s" % (p, sy, st))
        if cb is None or not sp:
            continue
        x0, y0, x1, y1 = a["box"]
        w = x1 - x0
        m_i = int(m)
        cells = staff_cells[(p, sy, st)]
        first = min(cells)
        last = max(cells)
        barl = sorted(sys_edges[(p, sy)])
        near = lambda x: min(abs(x - e) for e in barl) / sp      # noqa: E731
        hb = heads["/".join([p, sy, st])]
        near_head = lambda x: min((0.0 if h[0] <= x <= h[2] else min(abs(x - h[0]), abs(x - h[2])) for h in hb), default=99) / sp    # noqa: E731
        r = dict(key=ak, cls=a["cls"], page=int(p), staff="%s/%s/%s" % (p, sy, st), cell=m_i, sp=sp, box=a["box"], w_sp=w / sp,
                 cellw_sp=(cb[2] - cb[0]) / sp,
                 l_edge=abs(x0 - cb[0]) / sp, r_edge=abs(cb[2] - x1) / sp,
                 l_bar=near(x0), r_bar=near(x1), l_head=near_head(x0), r_head=near_head(x1),
                 l_interior=m_i != first, r_interior=m_i != last,
                 curve=piece_curve.get(ak), absn=absn.get(ak))
        # chance: slide the box inside the cell
        lo, hi = cb[0], cb[2] - w
        ce = be = he = n = cl = cr = 0
        for _ in range(200):
            s0 = rng.uniform(lo, hi) if hi > lo else lo
            n += 1
            cl += abs(s0 - cb[0]) <= 0.25 * sp
            cr += abs(cb[2] - (s0 + w)) <= 0.25 * sp
            ce += (abs(s0 - cb[0]) <= TOL * sp) + (abs(cb[2] - (s0 + w)) <= TOL * sp)
            be += (near(s0) <= TOL) + (near(s0 + w) <= TOL)
            he += (near_head(s0) <= TOL) + (near_head(s0 + w) <= TOL)
        r["chance_cell"], r["chance_bar"], r["chance_head"] = ce / n, be / n, he / n
        r["chance_l25"], r["chance_r25"] = cl / n, cr / n
        rows.append(r)
    # edge pairs: right-cut box in cell m with left-cut box in cell m+1 of the same staff, y ranges overlapping
    by_staff = collections.defaultdict(list)
    for r in rows:
        by_staff[r["staff"]].append(r)
    for r in rows:
        r["cut_l"] = r["l_edge"] <= TOL and r["l_interior"]
        r["cut_r"] = r["r_edge"] <= TOL and r["r_interior"]
        r["partner_l"] = r["partner_r"] = None
    for st, rs in by_staff.items():
        for a in rs:
            if not a["cut_r"]:
                continue
            for b in rs:
                if b["cell"] != a["cell"] + 1 or not b["cut_l"]:
                    continue
                ya, yb = a["box"], b["box"]
                if ya[1] - 0.5 * a["sp"] <= yb[3] and yb[1] - 0.5 * a["sp"] <= ya[3]:
                    a["partner_r"] = a["partner_r"] or b["key"]
                    b["partner_l"] = b["partner_l"] or a["key"]
    json.dump(dict(plate=plate, gaps=[min(gaps), max(gaps), len(gaps)] if gaps else None, rows=rows, curves={k: dict(cells=v["detail"].get("cells"),
              pieces=v["detail"].get("pieces"), x_left=v["detail"].get("x_left_page"), x_right=v["detail"].get("x_right_page"),
              cut=v["detail"].get("cut_at_barline")) for k, v in curves.items()}), open(out, "w"))
    print(plate, "arc boxes", len(rows), "cells gap min/max", (min(gaps), max(gaps)) if gaps else None)


if __name__ == "__main__":
    main()
