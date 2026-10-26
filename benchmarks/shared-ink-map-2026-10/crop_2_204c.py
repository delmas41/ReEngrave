"""2.204c read-only crop check: 24 of the Litolff `disagree` heads (seed 2204), stratified 9 wrong_side / 6 barline / 9 not_a_stroke.
Own look: head orange, finder stem BLUE, stroke candidates RED (accepted or refused, labelled). Blind sheet: 12 of the 24, orange box on the head only.
Run from a worktree that has out/lane-report/2.204/work and the library: python3 crop_2_204c.py OUTDIR"""
import json, pathlib, random, sys, collections
ROOT = pathlib.Path.cwd(); sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
W = ROOT / "out/lane-report/2.204/work/"
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
on = json.load(open(W / "litolff.on.gathered.record.json"))["record"]
off = json.load(open(W / "litolff.off.gathered.record.json"))["record"]
od = {v["subject"]: v for v in off["verdicts"] if v["quantity"] == "duration"}
obs = {o["id"]: o for o in on["observations"]}
by_sub = collections.defaultdict(list)
for o in on["observations"]:
    by_sub[o["subject"]].append(o)
cellstroke = collections.defaultdict(list)
for o in on["observations"]:
    if o["quantity"] == "stroke" and o["detail"].get("bbox_page_px") and o["detail"].get("stroke_box"):
        cellstroke["/".join(o["subject"].split("/")[:5]).replace("glyph", "cell")].append(o)
pop = []
for v in on["verdicts"]:
    if v["quantity"] != "duration": continue
    sf = (v.get("detail") or {}).get("stems_from_strokes")
    if sf and sf["settled"] == "disagree" and od.get(v["subject"], {}).get("outcome") == "decided":
        kind = {"finder_stem_but_wrong_side": "wrong_side", "finder_stem_but_barline": "barline",
                "finder_stem_is_not_a_stroke_beside_the_head": "not_a_stroke"}[sf["disagree"]]
        pop.append((kind, v))
cnt = collections.Counter(k for k, _ in pop); print(len(pop), cnt)
rng = random.Random(2204)
quota = {"wrong_side": 9, "barline": 6, "not_a_stroke": 9}
items = []
for k, n in quota.items():
    pl = sorted([v for kk, v in pop if kk == k], key=lambda v: v["subject"]); rng.shuffle(pl)
    items += [(k, v) for v in pl[:n]]
def fit(cell):
    # cell px -> page px: x_page = a*x + b, from the cell's strokes (least squares on both corners)
    xs, ys, XP, YP = [], [], [], []
    for s in cellstroke[cell]:
        x, y, w, h = s["detail"]["stroke_box"]; b = s["detail"]["bbox_page_px"]
        xs += [x, x + w]; XP += [b[0], b[2]]; ys += [y, y + h]; YP += [b[1], b[3]]
    def lin(a, b):
        n = len(a); ma, mb = sum(a)/n, sum(b)/n
        s = sum((i-ma)**2 for i in a) or 1
        k = sum((i-ma)*(j-mb) for i, j in zip(a, b))/s
        return k, mb - k*ma
    return lin(xs, XP), lin(ys, YP)
rows = []
cache = {}
u = 15.75
for n, (kind, v) in enumerate(items, 1):
    sub = v["subject"]; pg = int(sub.split("/")[1]); cell = "/".join(sub.split("/")[:5]).replace("glyph", "cell")
    head = [o for o in by_sub[sub] if o["quantity"] == "glyph_box" and o["detail"].get("bbox_page_px")][0]["detail"]["bbox_page_px"]
    (ax, bx), (ay, by) = fit(cell)
    sf = v["detail"]["stems_from_strokes"]
    fstems = [obs[i] for i in v["detail"]["used"] + v["considered"] if i in obs and obs[i]["quantity"] == "stem"]
    seen = set(); fb = []
    for s in fstems:
        if s["id"] in seen: continue
        seen.add(s["id"]); x, y, w, h = s["value"]
        bb = [ax*x+bx, ay*y+by, ax*(x+w)+bx, ay*(y+h)+by]
        if bb[2] >= head[0]-u*0.8 and bb[0] <= head[2]+u*0.8 and bb[3] >= head[1] and bb[1] <= head[3]: fb.append(bb)
    cands = []
    for c in sf["candidates"]:
        for r in c["rows"]:
            cands.append((obs[r]["detail"]["bbox_page_px"], c["why"], c["side"], c["direction"], c["length_sp"]))
    if pg not in cache:
        cache.clear(); cache[pg] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES["litolff"]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    im = cache[pg]
    cx, cy = (head[0]+head[2])/2, (head[1]+head[3])/2
    x0, y0, x1, y1 = max(0, int(cx-5*u)), max(0, int(cy-9*u)), int(cx+5*u), int(cy+9*u)
    im.crop((x0, y0, x1, y1)).resize(((x1-x0)*2, (y1-y0)*2), Image.LANCZOS).save(out / ('raw_%02d.png' % n))
    for blind in (0, 1):
        cr = im.crop((x0, y0, x1, y1)).copy(); d = ImageDraw.Draw(cr)
        def R(b, col, w=2): d.rectangle([b[0]-x0, b[1]-y0, b[2]-x0, b[3]-y0], outline=col, width=w)
        if blind:
            R([head[0]-4, head[1]-4, head[2]+4, head[3]+4], (255, 140, 0), 3)
        else:
            R(head, (255, 140, 0), 2)
            for b in fb: R([b[0]-3, b[1], b[2]+3, b[3]], (0, 80, 255), 2)
            for b, why, side, dr, L in cands: R([b[0]-1, b[1], b[2]+1, b[3]], (230, 0, 0), 1)
            d.text((3, 3), "#%d %s fs=%d" % (n, kind, len(fb)), fill=(0, 0, 0))
        cr = cr.resize((cr.width*2, cr.height*2), Image.LANCZOS)
        cr.save(out / (("blind_%02d" if blind else "look_%02d") % n + ".png"))
    rows.append(dict(n=n, kind=kind, subject=sub, page=pg, box=head, finder=fb, cands=[(c[1], c[2], c[3], c[4]) for c in cands],
                     state=sf["state"], was=od[sub]["value"], plate="litolff"))
json.dump(rows, open(out / "sample.json", "w"), indent=1, default=str)
for r in rows: print(r["n"], r["kind"], r["page"], r["state"], len(r["finder"]), r["cands"])
