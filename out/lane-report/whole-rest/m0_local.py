"""whole-rest m0: measure the refused/kept restWhole boxes LOCALLY on the print (600 dpi raster): the staff lines at the box's x
(left and right of the box, interpolated across it), the rest block's own ink in the box's middle columns, and how many LOCAL lines
the rest's INK touches (not the detector box).
usage: m0_local.py PLATE GEOM.json OUT.json [N_KEPT_SAMPLE]"""
import json, sys, random, collections, statistics as S
import numpy as np
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
plate, gj, outp = sys.argv[1:4]
nk = int(sys.argv[4]) if len(sys.argv) > 4 else 40
rows = json.load(open(gj))
boxes = {}
import pickle
d = pickle.load(open(gj.replace(".geom.json", ""), "rb"))
for o in d["observations"]:
    if o["quantity"] == "glyph_box" and o["value"][0] == "restWhole":
        bb = (o.get("detail") or {}).get("bbox_page_px")
        if bb:
            boxes[o["subject"]] = bb
random.seed(1)
sel = [r for r in rows if r["reason"] in ("rest_touches_two_staff_lines", "rest_off_center")]
kept = [r for r in rows if r["reason"] == "KEPT"]
sel += random.sample(kept, min(nk, len(kept)))
sel.sort(key=lambda r: int(r["sub"].split("/")[1]))
cache = {}; res = []
for r in sel:
    pg = int(r["sub"].split("/")[1])
    if pg not in cache:
        cache.clear()
        cache[pg] = np.asarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb)
    im = cache[pg]
    if im.ndim == 3:
        im = im.mean(axis=2)
    dark = im < 140
    bb = boxes[r["sub"]]; x0, y0, x1, y1 = [float(v) for v in bb]
    sp = r["space"]; lines = r["lines"]
    def local_lines(xa, xb):
        xa, xb = int(max(0, xa)), int(xb)
        prof = dark[:, xa:xb].mean(axis=1)
        out = []
        for ly in lines:
            lo, hi = int(ly - 0.6 * sp), int(ly + 0.6 * sp)
            seg = prof[lo:hi]
            if seg.max() < 0.6:
                out.append(None); continue
            idx = np.where(seg >= 0.6 * seg.max())[0]
            out.append(lo + float(idx.mean()))
        return out
    L_ = local_lines(x0 - 2.0 * sp, x0 - 0.4 * sp)
    R_ = local_lines(x1 + 0.4 * sp, x1 + 2.0 * sp)
    loc = [None if (a is None and b is None) else (a if b is None else b if a is None else (a + b) / 2) for a, b in zip(L_, R_)]
    tilt = [None if (a is None or b is None) else (b - a) / sp for a, b in zip(L_, R_)]
    # the rest block's ink: middle third columns of the box, rows within the box padded 0.3 sp
    cx0, cx1 = int(x0 + (x1 - x0) / 3), int(x1 - (x1 - x0) / 3)
    prof = dark[:, cx0:cx1].mean(axis=1)
    yy0, yy1 = int(y0 - 0.5 * sp), int(y1 + 0.5 * sp)
    inkrows = np.where(prof[yy0:yy1] >= 0.7)[0] + yy0
    # the block = contiguous run of ink rows that is thicker than a line (> 0.25 sp) or the lowest ink run in the box
    runs = []
    if len(inkrows):
        s = inkrows[0]; p = inkrows[0]
        for y in inkrows[1:]:
            if y != p + 1:
                runs.append((s, p)); s = y
            p = y
        runs.append((s, p))
    thick = [rr for rr in runs if (rr[1] - rr[0] + 1) > 0.28 * sp]
    blk = max(thick, key=lambda rr: rr[1] - rr[0]) if thick else None
    rec = dict(sub=r["sub"], reason=r["reason"], space=sp, tilt_sp=[round(t, 3) for t in tilt if t is not None], n_local=sum(v is not None for v in loc))
    if blk and all(v is not None for v in loc):
        top, bot = blk
        # line index the block hangs from: the local line nearest the block's top edge
        k = min(range(5), key=lambda j: abs(loc[j] - top))
        rec.update(block_h_sp=round((bot - top + 1) / sp, 2), top_vs_line_sp=round((top - loc[k]) / sp, 2), k=k,
                   gap_below_sp=round((loc[k + 1] - bot) / sp, 2) if k < 4 else None,
                   box_bottom_gap_sp=round((loc[k + 1] - y1) / sp, 2) if k < 4 else None,
                   box_top_vs_line_sp=round((y0 - loc[k]) / sp, 2))
        # lines touched by the INK block (tolerance 0.25 sp as the rule uses): top edge or bottom edge within tol of a line, or a line inside
        tol = 0.25 * sp
        rec["ink_lines_touched"] = sum(1 for v in loc if abs(v - top) <= tol or abs(v - bot) <= tol or top - tol <= v <= bot + tol)
        rec["box_lines_touched_local"] = sum(1 for v in loc if abs(v - y0) <= tol or abs(v - y1) <= tol or y0 - tol <= v <= y1 + tol)
    res.append(rec)
json.dump(res, open(outp, "w"))
by = collections.defaultdict(list)
for q in res:
    by[q["reason"]].append(q)
for k, v in by.items():
    ok = [q for q in v if "block_h_sp" in q]
    print(k, "n", len(v), "measured", len(ok))
    if ok:
        print("  ink block h sp med %.2f; hangs from line idx %s" % (S.median(q["block_h_sp"] for q in ok), collections.Counter(q["k"] for q in ok).most_common()))
        print("  block top vs LOCAL line sp: med %.2f ; box top vs local line: med %.2f" % (S.median(q["top_vs_line_sp"] for q in ok), S.median(q["box_top_vs_line_sp"] for q in ok)))
        g = [q["gap_below_sp"] for q in ok if q["gap_below_sp"] is not None]
        bg = [q["box_bottom_gap_sp"] for q in ok if q["box_bottom_gap_sp"] is not None]
        print("  INK bottom to next local line below: med %.2f min %.2f ; BOX bottom to it: med %.2f min %.2f" % (S.median(g), min(g), S.median(bg), min(bg)))
        print("  lines touched by the INK (tol .25): %s ; by the BOX vs local lines: %s" % (collections.Counter(q["ink_lines_touched"] for q in ok), collections.Counter(q["box_lines_touched_local"] for q in ok)))
        t = [abs(x) for q in ok for x in q["tilt_sp"]]
        print("  local tilt across the box |sp| med %.3f max %.3f" % (S.median(t), max(t)) if t else "")
