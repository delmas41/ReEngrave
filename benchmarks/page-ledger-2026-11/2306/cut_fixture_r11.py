"""2306 r11 real-case fixtures (CLAUDE rule 7: the pixels of marks Sean has named), cut from the r9 gathers (OMR_PAGE_STEMS=1): around each of Sean's
r10 tiles (ten printed stems the page reader refused, two non-notes) and the r10 chord controls (Litolff p10 glyph/10/0/1/11/0, /6/0) -- the page
heads (the reader's own groups, from the Q.PAGE_STEM rows' head ids; the 2.290 oval where there is one, else the strongest box; the head claim's own
strokes), the vertical pieces, the other strokes as crossers, held strokes, and every stroke in the window with the page map's `touches`.
Usage: cut_fixture_r11.py LIT_REC BRA_REC OUT.json"""
import sys, os, json, collections

TILES = {
    "litolff": [("t1", "glyph/6/1/1/12/0"), ("t2", "glyph/6/1/1/10/7"), ("t6", "glyph/4/1/0/8/1"), ("t7", "glyph/10/1/7/7/2"), ("t8", "glyph/2/0/0/1/1"),
                ("t9", "glyph/6/1/1/1/3"), ("t11", "glyph/10/0/1/8/1"), ("t12", "glyph/6/0/1/8/9"), ("c_10_0_1_11_0", "glyph/10/0/1/11/0"),
                ("c_10_0_1_6_0", "glyph/10/0/1/6/0"), ("wide_lit", "glyph/10/1/0/14/6"),
                # ROADMAP 2.306 r12: Sean's r11 tiles -- lost eighths 8 (4/1/2/4/0, on r4 tile 5's run) and 5 (9/0/0/0/3, a chord whose stroke the
                # page reads both ways), the fake 6 (a sharp written as a note), and r8 tile 3 (a second on one stem: the join must hold)
                ("r11t8", "glyph/4/1/2/4/0"), ("r11t5", "glyph/9/0/0/0/3"), ("r11t6_sharp", "glyph/6/1/2/10/3"), ("r8t3_second", "glyph/4/1/2/5/1")],
    "brahms": [("t3", "glyph/25/1/7/3/2"), ("t4", "glyph/12/0/10/7/5"), ("t5", "glyph/14/1/4/3/7"), ("t10", "glyph/12/0/7/0/14"), ("wide_bra", "glyph/4/1/12/8/7"),
               ("divisi_bra", "glyph/5/0/12/3/10")],
}
SEAN = {"t1": "down", "t2": "down", "t3": "down", "t4": "not a note (tremolo slash)", "t5": "up", "t6": "down", "t7": "up", "t8": "down", "t9": "up",
        "t10": "up", "t11": "down", "t12": "not a note (part of a p dynamic)",
        "wide_lit": "wide chord on one long stem (Sean's r1 tile 7: 'a long stem on a chord')",
        "wide_bra": "wide chord on one stem, 4 heads over 6.3 sp (r4 tile 9's chord, Sean: eighth)",
        "divisi_bra": "two voices end to end (the r4 divisi pair): never one stem",
        "r11t8": "eighth (r11 tile 8; r4 tile 5 -- 4/1/2/4/11 -- an eighth on the same run)", "r11t5": "eighth (r11 tile 5; its chord mates 11, 14)",
        "r11t6_sharp": "a sharp sign (r11 tile 6): never a note", "r8t3_second": "eighth on a stem through its second (r4 tile 3, r8)"}


def parts(rec_path, pages):
    R = json.load(open(rec_path))["record"]
    pg = lambda s: int(s.split("/")[1])
    P = collections.defaultdict(lambda: dict(gbox={}, gconf={}, claims={}, groups=collections.defaultdict(set), strokes={}, held={}))
    for o in R["observations"]:
        s = o["subject"]
        if not s.startswith(("page/", "glyph/")) or pg(s) not in pages:
            continue
        p, q, d = pg(s), o["quantity"], (o.get("detail") or {})
        X = P[p]
        if q == "glyph_box" and d.get("bbox_page_px"):
            X["gbox"][s] = [float(v) for v in d["bbox_page_px"]]
            X["gconf"][s] = float(o.get("score") or 0)
        elif q == "claimed_area" and d.get("source") == "page_head_one" and o["value"] != "census":
            for m in d.get("members") or ():
                X["claims"][m] = d
        elif q == "claimed_area" and d.get("page_strokes") and o["value"] != "census" and d.get("owner") not in ("head", "stem") \
                and d.get("standing", "READ") == "READ":
            for i in d["page_strokes"]:
                X["held"].setdefault(int(i), d.get("owner"))
        elif q == "page_stroke":
            X["strokes"][int(d["ordinal"])] = dict(kind=o["value"], box=[float(v) for v in d["bbox_page_px"]], touches=d.get("touches") or [],
                                                   sp=float(d.get("staff_space_local_px") or 0) or None, th=float(d.get("thickness_spaces") or 0))
        elif q == "page_stem" and d.get("head") is not None:
            X["groups"][int(d["head"])].add(s)
    for a in R["abstentions"]:
        d = a.get("detail") or {}
        if a["quantity"] == "page_stem" and pg(a["subject"]) in pages and d.get("head") is not None:
            P[pg(a["subject"])]["groups"][int(d["head"])].add(a["subject"])
    return P


def cut(X, glyph, wx=140, wy=220):
    hb = X["gbox"][glyph]
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    W = (cx - wx, cy - wy, cx + wx, cy + wy)
    m = lambda b: b[0] <= W[2] and b[2] >= W[0] and b[1] <= W[3] and b[3] >= W[1]
    heads = []
    for gi, mem in X["groups"].items():
        mem = sorted(mem)
        cl = next((X["claims"][k] for k in mem if k in X["claims"]), None)
        if cl and cl.get("oval"):
            box, ink = [float(v) for v in cl["oval"]], True
        else:
            k = max((k for k in mem if k in X["gbox"]), key=lambda k: X["gconf"].get(k, 0), default=None)
            if k is None:
                continue
            box, ink = X["gbox"][k], False
        if m(box):
            heads.append(dict(id=gi, members=mem, box=box, sp=30.0, ink=ink, strokes=[int(i) for i in ((cl or {}).get("page_strokes") or [])]))
    verts, cross, strokes = [], [], {}
    for o, s in X["strokes"].items():
        if not m(s["box"]):
            continue
        strokes[str(o)] = dict(box=s["box"], kind=s["kind"], touches=s["touches"])
        if s["kind"] == "barline":
            continue
        if s["kind"] == "vertical":
            verts.append(dict(ord=o, box=s["box"], sp=s["sp"] or 30.0))
        else:
            k = "slash" if X["held"].get(o) == "tremolo" else ("beam" if s["kind"] == "horizontal" and s["th"] >= 0.4 else s["kind"])
            cross.append(dict(ord=o, box=s["box"], kind=k))
    held = {str(o): v for o, v in X["held"].items() if str(o) in strokes}
    return dict(heads=heads, verticals=verts, crossers=cross, held=held, strokes=strokes, window=[round(v) for v in W])


out = {"about": "ROADMAP 2.306 r11 real-case fixtures (Sean's r10 tiles + the r10 chord controls), cut by benchmarks/page-ledger-2026-11/2306/"
                "cut_fixture_r11.py from the r9 gathers 2306-r9-lit / 2306-r9-bra (page px, 600 dpi). sean = his answer."}
for plate, rp in (("litolff", sys.argv[1]), ("brahms", sys.argv[2])):
    P = parts(rp, {int(g.split("/")[1]) for _n, g in TILES[plate]})
    for name, g in TILES[plate]:
        p = int(g.split("/")[1])
        out[name] = dict(plate=plate, page=p, glyph=g, sean=SEAN.get(name, "chord control (r10)"), **cut(P[p], g))
    del P
json.dump(out, open(sys.argv[3], "w"), separators=(",", ":"))
print({k: (len(v["heads"]), len(v["verticals"]), len(v["strokes"])) for k, v in out.items() if isinstance(v, dict)})
