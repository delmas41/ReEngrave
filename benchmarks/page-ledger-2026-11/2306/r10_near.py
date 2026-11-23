"""2306 r10 (measurement only): the real heads the page stem reader leaves with NO stroke although verticals lie near ("no_stroke", nothing held, near
non-empty), and the cell join still stems them. For each: rebuild the page reader's input offline from the gather (page heads = the 2.290 head claims'
ovals, else the strongest member box; verticals = the page map's vertical strokes joined into runs with `page_stems.join_runs`), check the offline
reading reproduces the gathered abstention, then measure the NEAREST vertical against each test of `page_stems._fits` on the side the OLD cell join
says the stem is on (up -> right edge, down -> left edge): dx from the edge (|dx| <= EDGE_SP), reach past the head centre (>= REACH_SP), head-end gap
(<= GAP_SP); the first test it fails and by how much. Splits: hollow/filled, in staff/ledger, chord/single, beamed/not, oval/detector box.
Usage (cwd = tree): r10_near.py REC.json RFPREFIX OUT.json"""
import sys, os, json, re, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS

rec_p, pre, out_p = sys.argv[1:4]
R = json.load(open(rec_p))["record"]
obs, abst = R["observations"], R["abstentions"]
pg = lambda s: int(s.split("/")[1])
gbox, gcls, gconf = {}, {}, {}
claims = collections.defaultdict(dict)        # page -> gi -> claim detail (members, oval)
strokes = collections.defaultdict(list)
held = collections.defaultdict(dict)
page_stem_read = set()
hgroups = collections.defaultdict(dict)       # page -> head id (the reader's own) -> glyph keys
for o in obs:
    q, d = o["quantity"], (o.get("detail") or {})
    if q == "glyph_box" and d.get("bbox_page_px"):
        gbox[o["subject"]] = tuple(float(v) for v in d["bbox_page_px"])
        gcls[o["subject"]] = str(o["value"][0])
        gconf[o["subject"]] = float(o.get("score") or 0)
    elif q == "claimed_area" and d.get("source") == "page_head_one" and o["value"] != "census":
        claims[pg(o["subject"])][int(o["value"])] = d
    elif q == "page_stroke":
        strokes[pg(o["subject"])].append(dict(ord=int(d["ordinal"]), kind=o["value"], box=tuple(float(v) for v in d["bbox_page_px"]),
                                              sp=float(d.get("staff_space_local_px") or 0) or None, th=float(d.get("thickness_spaces") or 0),
                                              comp=d.get("component"), length=float(d.get("length_spaces") or 0)))
    elif q == "claimed_area" and d.get("page_strokes") and o["value"] != "census" and d.get("owner") not in ("head", "stem") \
            and d.get("standing", "READ") == "READ":
        for i in d["page_strokes"]:
            held[pg(o["subject"])].setdefault(int(i), d.get("owner"))
    elif q == "page_stem":
        page_stem_read.add(o["subject"])
        if d.get("head") is not None:
            hgroups[pg(o["subject"])].setdefault(int(d["head"]), set()).add(o["subject"])
abd = {a["subject"]: a.get("detail") or {} for a in abst if a["quantity"] == "page_stem"}
for a in abst:
    if a["quantity"] == "page_stem" and (a.get("detail") or {}).get("head") is not None:
        hgroups[pg(a["subject"])].setdefault(int(a["detail"]["head"]), set()).add(a["subject"])
oval_of = {}
for p_, cl in claims.items():
    for _gi, d in cl.items():
        if d.get("oval"):
            for m in d.get("members") or ():
                oval_of[(p_, m)] = d["oval"]
del R, obs, abst

A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
LA, LB = collections.defaultdict(dict), collections.defaultdict(dict)
for D, L in ((A, LA), (B, LB)):
    for v in D["verdicts"]:
        L[v["s"]][v["q"]] = v


def real(g):
    n = LB[g].get("notehead_is_not_a_notehead")
    if n and n["o"] == "decided" and n["v"] is True:
        return False
    o = LB[g].get("glyph_owner")
    if o and o["o"] == "decided" and isinstance(o["v"], str) and o["v"] != "staff/" + "/".join(g.split("/")[1:4]):
        return False
    return "head_stem" in LB[g]


targets = [g for g, d in abd.items() if g not in page_stem_read and real(g) and LB[g]["head_stem"]["o"] == "decided"
           and d.get("note") == "no_stroke" and not d.get("held") and d.get("near")]
print("targets:", len(targets))

# offline page reader inputs, per page
cache = {}


def page_input(p):
    if p in cache:
        return cache[p]
    heads = []
    for gi, mem in hgroups[p].items():
        mem = sorted(mem)
        ov = next((o for o in (oval_of.get((p, m)) for m in mem) if o), None)
        d = {"oval": ov} if ov else {}
        if d.get("oval"):
            box, ink = tuple(float(v) for v in d["oval"]), True
        else:
            m = max((m for m in mem if m in gbox), key=lambda m: gconf.get(m, 0), default=None)
            if m is None:
                continue
            box, ink = gbox[m], False
        heads.append(dict(id=gi, members=mem, box=box, sp=30.0, ink=ink))
    verts = [dict(ord=s["ord"], box=s["box"], sp=s["sp"]) for s in strokes[p] if s["kind"] == "vertical"]
    cross = [dict(ord=s["ord"], box=s["box"], kind=("slash" if held[p].get(s["ord"]) == "tremolo" else ("beam" if s["kind"] == "horizontal" and s["th"] >= 0.4
                                                                                                      else s["kind"]))) for s in strokes[p] if s["kind"] != "vertical"]
    res = PS.read(heads, verts, held[p], crossers=cross)
    runs, _ = PS.join_runs(verts, heads, cross, held[p])
    joined = {m for r in runs for m in r["members"]}
    rv = [dict(ord=r["ord"], box=r["box"], sp=r["sp"], members=r["members"]) for r in runs] + \
         [dict(v, members=[v["ord"]]) for v in verts if v["ord"] not in joined]
    cache[p] = (heads, rv, res, {s["ord"]: s for s in strokes[p]})
    return cache[p]


rows = []
for g in sorted(targets):
    p = pg(g)
    heads, rv, res, sby = page_input(p)
    h = next((h for h in heads if g in h["members"]), None)
    if h is None:
        rows.append(dict(g=g, why="no page head holds it offline"))
        continue
    r = res["heads"][h["id"]]
    x0, y0, x1, y1 = h["box"]
    cy = (y0 + y1) / 2.0
    dir_old = (LA[g].get("stem_direction") or {}).get("v")
    best = None
    for v in rv:
        sp = float(v["sp"] or 30.0)
        sx0, sy0, sx1, sy1 = v["box"]
        if sx1 < x0 - 2.5 * sp or sx0 > x1 + 2.5 * sp:
            continue
        if sy1 < y0 - 6 * sp or sy0 > y1 + 6 * sp:
            continue
        sxc = (sx0 + sx1) / 2.0
        for side, direction in (("right", "up"), ("left", "down")):
            if dir_old in ("up", "down") and direction != dir_old:
                continue
            dx = (sxc - (x1 if side == "right" else x0)) / sp
            reach = ((cy - sy0) if direction == "up" else (sy1 - cy)) / sp
            gap = ((cy - sy1) if direction == "up" else (sy0 - cy)) / sp
            fails = []
            if abs(dx) > PS.EDGE_SP:
                fails.append(("x_off_edge", round(abs(dx) - PS.EDGE_SP, 2)))
            if reach < PS.REACH_SP:
                fails.append(("reach_short", round(PS.REACH_SP - reach, 2)))
            if gap > PS.GAP_SP:
                fails.append(("head_end_too_far", round(gap - PS.GAP_SP, 2)))
            score = sum(m for _k, m in fails) + (0 if dx * (1 if side == "right" else -1) <= 0.0 or abs(dx) <= PS.EDGE_SP else 0)
            cand = dict(stroke=v["ord"], members=v["members"], side=side, direction=direction, dx=round(dx, 2), dx_out=round(dx if side == "right" else -dx, 2), sp=sp, head_w=round((x1 - x0) / sp, 2), reach=round(reach, 2), gap=round(gap, 2),
                        length=round((sy1 - sy0) / sp, 2), fails=fails, score=round(score, 2), held=held[p].get(v["ord"]),
                        inside_head=bool(sx0 >= x0 and sx1 <= x1))
            if best is None or cand["score"] < best["score"]:
                best = cand
    off_dur = (LA[g].get("duration") or {}).get("v")
    pos = LA[g].get("notehead_position") or {}
    n_same = sum(1 for s, qs in LA.items() if s.startswith("/".join(g.split("/")[:5]) + "/") and (qs.get("head_stem") or {}).get("v") == LA[g]["head_stem"]["v"])
    rows.append(dict(
        g=g, offline=r["how"], gathered=abd[g].get("how"), head_box=[round(v) for v in h["box"]], oval=h["ink"],
        head_w_sp=round((x1 - x0) / 30.0, 2), cls=gcls.get(g), hollow=("Half" in str(gcls.get(g)) or "Whole" in str(gcls.get(g)) or
                                                                 (isinstance(off_dur, dict) and float(off_dur.get("written") or 0) >= 2.0)),
        ledger=(pos.get("r") == "ledger_position"), pos=pos.get("v"), chord=n_same > 1, beamed=bool(isinstance(off_dur, dict) and (off_dur.get("beam_levels") or 0) >= 1),
        old_dir=dir_old, old_stem=LA[g]["head_stem"]["v"], nearest=best))
json.dump(rows, open(out_p, "w"), indent=0, default=str)
ok = sum(1 for r in rows if r.get("offline") == "no_stroke")
print("offline reproduces no_stroke:", ok, "of", len(rows), collections.Counter(r.get("offline") for r in rows))


def first_fail(r):
    b = r.get("nearest")
    if not b:
        return "no vertical within 2.5 sp x / 6 sp y"
    f = b["fails"]
    return "+".join(k for k, _m in f) if f else "passes (refused elsewhere)"


print("\nfirst failing test of the nearest vertical on the OLD join's side:")
for k, n in collections.Counter(first_fail(r) for r in rows).most_common():
    print("  %4d  %s" % (n, k))


def hist(vals, edges):
    c = collections.Counter()
    for v in vals:
        lab = next(("<=%s" % e for e in edges if v <= e), ">%s" % edges[-1])
        c[lab] += 1
    return [(("<=%s" % e), c.get("<=%s" % e, 0)) for e in edges] + [(">%s" % edges[-1], c.get(">%s" % edges[-1], 0))]


for key, edges in (("x_off_edge", [0.1, 0.2, 0.3, 0.5, 1.0]), ("reach_short", [0.25, 0.5, 1.0, 1.5]), ("head_end_too_far", [0.25, 0.5, 1.0, 2.0])):
    vals = [m for r in rows if r.get("nearest") for k, m in r["nearest"]["fails"] if k == key]
    print("%-17s by how much past the cut (sp): %s" % (key, hist(vals, edges)))
dxs = [r["nearest"]["dx_out"] for r in rows if r.get("nearest")]
print("signed dx of the nearest vertical from the engraving edge (sp, + = outward, away from the head):", hist([d if True else d for d in dxs], [-1.0, -0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 1.0]))
print("\nsplits (targets):")
for name in ("hollow", "ledger", "chord", "beamed", "oval", "old_dir"):
    print("  %-7s %s" % (name, dict(collections.Counter(r.get(name) for r in rows))))
print("  first fail x hollow:", dict(collections.Counter((first_fail(r), r.get("hollow")) for r in rows)))
