"""2306 r10 (measurement): for r10_near's reproduced no_stroke heads, two further facts per head --
  chord_gap: between this head and its nearest vertical's head end, how much of the stem's column is NOT covered by another page head (sp) -- i.e. is the
             stroke's far start explained by chord mates stacked against this head (heads touching: the stem starts at the far one);
  ink edges: the head's own ink extent on the raster at its centre row band (contiguous run from the box centre), and the nearest vertical's dx from
             that INK edge instead of the box edge (the reader measures from the box: the 2.290 oval where there is one, else the detector box).
Also, for hollow heads in the staff, what the page map holds in the stem column on the old join's side: pieces, kinds, and whether the column is inked.
Usage (cwd = tree): r10_more.py DUMP.json REC.json PDF OUT.json"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
import numpy as np
from tools.omr.preprocessing import render_page
dump, rec_p, pdf, outp = sys.argv[1:5]
rows = [r for r in json.load(open(dump)) if r.get("offline") == "no_stroke"]
R = json.load(open(rec_p))["record"]
pg = lambda s: int(s.split("/")[1])
need = {pg(r["g"]) for r in rows}
heads_pg = collections.defaultdict(list)       # every page head box the reader used: from the page_stem rows' head ids + oval/box
ov = {}
gbox, gconf = {}, {}
hmem = collections.defaultdict(lambda: collections.defaultdict(set))
strokes = collections.defaultdict(list)
for o in R["observations"]:
    q, d = o["quantity"], (o.get("detail") or {})
    p = pg(o["subject"]) if o["subject"].startswith(("glyph/", "page/")) else None
    if p not in need:
        continue
    if q == "glyph_box" and d.get("bbox_page_px"):
        gbox[o["subject"]] = [float(v) for v in d["bbox_page_px"]]
        gconf[o["subject"]] = float(o.get("score") or 0)
    elif q == "claimed_area" and d.get("source") == "page_head_one" and d.get("oval"):
        for m in d.get("members") or ():
            ov[m] = [float(v) for v in d["oval"]]
    elif q == "page_stem" and d.get("head") is not None:
        hmem[p][int(d["head"])].add(o["subject"])
    elif q == "page_stroke":
        strokes[p].append(dict(ord=int(d["ordinal"]), kind=o["value"], box=[float(v) for v in d["bbox_page_px"]], len=d.get("length_spaces")))
for a in R["abstentions"]:
    if a["quantity"] == "page_stem" and pg(a["subject"]) in need and (a.get("detail") or {}).get("head") is not None:
        hmem[pg(a["subject"])][int(a["detail"]["head"])].add(a["subject"])
del R
for p, hs in hmem.items():
    for gi, mem in hs.items():
        b = next((ov[m] for m in mem if m in ov), None)
        if b is None:
            m = max((m for m in mem if m in gbox), key=lambda m: gconf.get(m, 0), default=None)
            b = gbox.get(m) if m else None
        if b:
            heads_pg[p].append((gi, sorted(mem), b))
out = []
rasters = {}
for r in rows:
    p = pg(r["g"])
    if p not in rasters:
        rasters[p] = render_page(pdf, p, dpi=600).rgb.mean(axis=2) < 128
    ink = rasters[p]
    st = r.get("nearest")
    x0, y0, x1, y1 = r["head_box"]
    cy = (y0 + y1) / 2.0
    sp = (st or {}).get("sp") or 16.0
    res = dict(g=r["g"], cls=None)
    # ink edges at the centre band
    band = ink[int(cy - 0.15 * sp):int(cy + 0.15 * sp) + 1, :]
    rowsum = band.any(axis=0)
    cx = int((x0 + x1) / 2)
    if rowsum[cx]:
        l = cx
        while l > 0 and rowsum[l - 1]:
            l -= 1
        rr = cx
        while rr < ink.shape[1] - 1 and rowsum[rr + 1]:
            rr += 1
        res["ink_lr"] = [l, rr]
        res["ink_w_sp"] = round((rr - l + 1) / sp, 2)
        res["box_w_sp"] = round((x1 - x0) / sp, 2)
        if st:
            sxc = st["dx"] * sp + (x1 if st["side"] == "right" else x0)
            e = rr if st["side"] == "right" else l
            res["dx_ink_out"] = round(((sxc - e) if st["side"] == "right" else (e - sxc)) / sp, 2)
    if st:
        # chord mates in the stem's column between this head and the stroke's head end
        sxc = st["dx"] * sp + (x1 if st["side"] == "right" else x0)
        if st["direction"] == "down":
            a, b = y1, cy + st["gap"] * sp
        else:
            a, b = cy - st["gap"] * sp, y0
        lo, hi = min(a, b), max(a, b)
        spans = []
        mates = []
        for gi, mem, hb in heads_pg[p]:
            if r["g"] in mem:
                continue
            if hb[0] - 0.4 * sp <= sxc <= hb[2] + 0.4 * sp and hb[3] > lo and hb[1] < hi:
                spans.append((max(hb[1], lo), min(hb[3], hi)))
                mates.append(mem[0])
        spans.sort()
        cov, edge = 0.0, lo
        for s0, s1 in spans:
            if s1 > edge:
                cov += s1 - max(s0, edge)
                edge = max(edge, s1)
        res["gap_len_sp"] = round((hi - lo) / sp, 2)
        res["gap_uncovered_sp"] = round(((hi - lo) - cov) / sp, 2)
        res["mates_in_gap"] = mates
        # column ink between the head edge and the stroke end
        col = ink[int(lo):int(hi) + 1, max(0, int(sxc - 2)):int(sxc + 3)]
        res["gap_col_inked"] = round(float(col.any(axis=1).mean()), 2) if col.size else None
    out.append(res)
json.dump(out, open(outp, "w"), indent=0)
print("written", len(out))
