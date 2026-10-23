"""2.192 blind tiles. usage: tiles.py OUTDIR  (reads /private/tmp/.../accdiff192.json + sample_contest json via env paths in the call).
Orange box on the ACCIDENTAL's own box (the ink in question); the crop holds the next note. Nothing else drawn. Key written outside the tile folder."""
import json, random, sys, os, collections
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
out, diffp, scp, slices = sys.argv[1:5]
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
U = {"litolff": 15.75, "brahms": 32.0}
diff = json.load(open(diffp)); sc = json.load(open(scp))
bbox = {}
for p in PDFS:
    for l in open("%s/%s/observations.jsonl" % (slices, p)):
        o = json.loads(l)
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") in ("accidental", "notehead"): bbox[o["subject"]] = (o["detail"] or {}).get("bbox_page_px")
rnd = random.Random(2192)
cases = []
for d in diff:
    for c in d["contested"]:
        cases.append(dict(plate=d["plate"], acc=c[0], head=d["head"], role="case", cls=c[1], off=d["off"], on=d["on"]))
byp = collections.defaultdict(list)
for c in cases: byp[c["plate"]].append(c)
pick = rnd.sample(sorted(byp["brahms"], key=lambda c: c["acc"]), 7) + rnd.sample(sorted(byp["litolff"], key=lambda c: c["acc"]), 2)
heads_used = {c["head"] for c in pick}
kept = [r for r in sc if r["keep"] and r["acc"] not in {c["acc"] for c in cases}]
ctl = rnd.sample(sorted(kept, key=lambda r: r["acc"]), 2)
for r in ctl:
    cell = "/".join(r["acc"].split("/")[:5])
    pick.append(dict(plate=r["plate"], acc=r["acc"], head=None, role="control_kept_by_the_flag", cls=r["cls"]))
# one control: a plain accidental with no rest box near
plain = []
for p in ("brahms",):
    for l in open("%s/%s/observations.jsonl" % (slices, p)):
        o = json.loads(l)
        if o["quantity"] == "glyph_box" and (o.get("detail") or {}).get("category") == "accidental" and o["value"][0] in ("accidentalSharp", "accidentalFlat") and o["subject"] not in {r["acc"] for r in sc}:
            plain.append(o["subject"])
a = rnd.choice(sorted(plain)); pick.append(dict(plate="brahms", acc=a, head=None, role="control_plain_accidental", cls="accidentalSharp/Flat"))
rnd.shuffle(pick)
os.makedirs(out + "/tiles", exist_ok=True); tiles = []; key = []; cache = {}
for k, t in enumerate(pick, 1):
    bb = bbox[t["acc"]]; pg = int(t["acc"].split("/")[1]); u = U[t["plate"]]
    hb = None
    if t["head"] and bbox.get(t["head"]): hb = bbox[t["head"]]
    if hb is None:    # nearest notehead to the right in the same cell
        cell = "/".join(t["acc"].split("/")[:5]); best = None
        for s, b in bbox.items():
            if s.startswith(cell + "/") and s != t["acc"] and b and b[0] > bb[2] - 5 and (best is None or b[0] < best[0]): best = b
        hb = best
    x1 = max(bb[2], hb[2]) if hb else bb[2]; y0 = min(bb[1], hb[1]) if hb else bb[1]; y1 = max(bb[3], hb[3]) if hb else bb[3]
    cx = (bb[0] + x1) / 2; cy = (y0 + y1) / 2
    if (t["plate"], pg) not in cache: cache.clear(); cache[(t["plate"], pg)] = Image.fromarray(render_page(PDFS[t["plate"]], pg, dpi=600).rgb).convert("RGB")
    im = cache[(t["plate"], pg)]
    X0, Y0, X1, Y1 = int(cx - 4.5 * u), int(cy - 3.3 * u), int(cx + 4.5 * u), int(cy + 3.3 * u)
    c = im.crop((X0, Y0, X1, Y1)).copy()
    ImageDraw.Draw(c).rectangle([bb[0] - X0 - 2, bb[1] - Y0 - 2, bb[2] - X0 + 2, bb[3] - Y0 + 2], outline=(255, 140, 0), width=3)
    c.save("%s/tiles/tile_%02d.png" % (out, k)); tiles.append(c)
    key.append(dict(tile=k, **t, page=pg, box=bb))
json.dump(key, open(out + "/key.json", "w"), indent=1)
TW = 500; cols = 3; rows = 4; th = int(tiles[0].size[1] * TW / tiles[0].size[0])
sheet = Image.new("RGB", (cols * (TW + 8), rows * (th + 22)), (255, 255, 255)); d = ImageDraw.Draw(sheet)
for k, t in enumerate(tiles):
    r_, c_ = divmod(k, cols); X, Y = c_ * (TW + 8), r_ * (th + 22)
    d.text((X + 3, Y + 3), str(k + 1), fill=(200, 0, 0)); sheet.paste(t.resize((TW, int(t.size[1] * TW / t.size[0]))), (X, Y + 16))
sheet.save(out + "/tiles/sheet.png"); print(len(pick), "tiles", collections.Counter(t["role"] for t in pick))
