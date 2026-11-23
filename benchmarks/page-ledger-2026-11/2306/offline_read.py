"""Run page_stems.read offline on a saved record's rows (heads from the page-head claim rows' ovals / detector boxes per page mark group,
verticals from Q.PAGE_STROKE, held from page-stroke claims only -- area claims and boxed accidentals NOT reproduced here)."""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged import page_stems as PS

path = sys.argv[1]
truth = sys.argv[sys.argv.index("--truth") + 1] if "--truth" in sys.argv else None
rec = load_record(path)["record"]
obs, vs = rec["observations"], rec["verdicts"]
pg = lambda s: int(s.split("/")[1])
by = collections.defaultdict(dict)
for v in vs:
    by[v["quantity"]][v["subject"]] = v
gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in obs if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("bbox_page_px")}
oval = {}
for o in obs:
    d = o.get("detail") or {}
    if o["quantity"] == "claimed_area" and d.get("source") == "page_head_one" and d.get("oval"):
        for m in d.get("members") or ():
            oval[m] = d["oval"]
groups = {}
for o in obs:
    if o["quantity"] == "page_mark" and (o.get("detail") or {}).get("family") == "head":
        groups[o["subject"]] = o["detail"]["members"]
pages = sorted({pg(s) for s in by["head_stem"]})
real = {s for s in by["head_stem"]} - {s for s, v in by["notehead_is_not_a_notehead"].items() if v["outcome"] == "decided" and v["value"] is True}
tot = collections.Counter()
allres = {}
for p in pages:
    heads = []
    for k, mem in groups.items():
        if pg(k) != p:
            continue
        b = next((oval[m] for m in mem if m in oval), None) or next((gbox[m] for m in mem if m in gbox), None)
        if b:
            heads.append(dict(id=k, members=mem, box=tuple(b), sp=30.0, ink=any(m in oval for m in mem)))
    verts, held = [], {}
    for o in obs:
        if o["quantity"] == "page_stroke" and pg(o["subject"]) == p and o["value"] == "vertical":
            d = o["detail"]
            verts.append(dict(ord=d["ordinal"], box=tuple(d["bbox_page_px"]), sp=d.get("staff_space_local_px") or 30.0))
        d = o.get("detail") or {}
        if o["quantity"] == "claimed_area" and pg(o["subject"]) == p and d.get("page_strokes") and d.get("owner") not in ("head", "stem"):
            for i in d["page_strokes"]:
                held.setdefault(int(i), d.get("owner"))
    for h in heads:          # local sp: the nearest vertical's (the reader uses the stroke's own)
        h["sp"] = 30.0
    res = PS.read(heads, verts, held)
    allres[p] = (res, {v["ord"]: v for v in verts})
    tot.update({k: v for k, v in res["census"].items() if isinstance(v, int)})
print("census:", dict(tot))
# A no_stem real heads
nost = {s for s in real if by["head_stem"][s]["outcome"] == "abstained" and by["head_stem"][s]["reason"] == "no_stem"}
mem2 = {}
for k, mem in groups.items():
    for m in mem:
        mem2[m] = k
c = collections.Counter()
for s in nost:
    k = mem2.get(s)
    if k is None:
        c["no_group"] += 1
        continue
    r = allres[pg(s)][0]["heads"].get(k)
    c[r["how"] if r else "no_head_box"] += 1
print("A no_stem heads", len(nost), dict(c))
if truth:
    T = json.load(open(truth))
    ts = [b["rect"] for b in T["boxes"] if b["cls"] == "stem"]
    res, vby = allres[0]
    mine = [vby[o]["box"] for o in res["stems"]]

    def hit(t, b):
        tx, bx = (t[0] + t[2]) / 2.0, (b[0] + b[2]) / 2.0
        ov = min(t[3], b[3]) - max(t[1], b[1])
        return abs(tx - bx) <= 8 and ov >= 0.5 * min(t[3] - t[1], b[3] - b[1])
    found = sum(1 for t in ts if any(hit(t, b) for b in mine))
    good = [b for b in mine if any(hit(t, b) for t in ts)]
    print("page stems vs Sean p0: truth %d found %d; read %d, on truth %d, not Sean's %d" % (len(ts), found, len(mine), len(good), len(mine) - len(good)))
    json.dump({"not_sean": [b for b in mine if not any(hit(t, b) for t in ts)], "missed": [t for t in ts if not any(hit(t, b) for b in mine)]},
              open(path + ".2306-p0-stems.json", "w"))
if "--both" in sys.argv:
    n = 0
    for p, (res, vby) in allres.items():
        for k, r in res["heads"].items():
            if r["how"] != sys.argv[sys.argv.index("--both") + 1] or n >= 14:
                continue
            n += 1
            c0 = r["candidates"][0]
            st = vby[c0["stroke"]]["box"]
            mem = groups[k]
            hs = by["head_stem"].get(mem[0])
            nn = by["notehead_is_not_a_notehead"].get(mem[0])
            print(k, mem[:2], "cand", [(c["direction"], c["stroke"], c["reach"], c["gap"]) for c in r["candidates"]], "stroke", [round(v) for v in st],
                  "A:", hs and (hs["outcome"], hs["reason"]), "refused" if nn and nn["value"] is True else "")
if "--missed" in sys.argv and truth:
    m = json.load(open(path + ".2306-p0-stems.json"))["missed"]
    res, vby = allres[0]
    hb = {}
    for k, mem in groups.items():
        if pg(k) == 0:
            b = next((oval[x] for x in mem if x in oval), None) or next((gbox[x] for x in mem if x in gbox), None)
            if b:
                hb[k] = b
    cc = collections.Counter()
    for t in m:
        tx = (t[0] + t[2]) / 2.0
        near = [k for k, b in hb.items() if b[0] - 25 <= tx <= b[2] + 25 and t[1] - 20 <= (b[1] + b[3]) / 2 <= t[3] + 20]
        hows = sorted({res["heads"][k]["how"] for k in near})
        cc[",".join(hows) or "no head near"] += 1
    print("missed Sean stems by the reading of the heads at them:", cc.most_common())
