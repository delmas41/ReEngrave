"""2306 blind tiles: places where a head's stem join CHANGED OFF -> ON (gained, removed, another stem), drawn at random (seeded) and stratified, one
staff per tile, ONE thin orange box on the stem (OFF's stem for a removal, ON's otherwise), the crop wide and tall enough that every head on it is whole.
Nothing else of ours drawn. Key outside the tile folder.
Usage: stem_tiles.py OUTDIR SEED N plate:REC.json:CHANGES.json:PDF [...]"""
import sys, os, json, random, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record

out, seed, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
specs = [a.split(":") for a in sys.argv[4:]]
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
rng = random.Random(seed)
pool = []
ctx = {}
for plate, rp, cp, pdf in specs:
    rec = load_record(rp)
    Q = M.rows_by_quantity(rec)
    geo = M.cell_geometry(Q)
    stem_val = {o["id"]: o["value"] for o in Q["stem"]}
    gbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in Q["glyph_box"] if (o.get("detail") or {}).get("bbox_page_px")}
    cellbox = {o["subject"]: o["value"] for o in Q["cell_box"]}
    ctx[plate] = dict(geo=geo, stem_val=stem_val, gbox=gbox, cellbox=cellbox, pdf=pdf)
    for c in json.load(open(cp)):
        c["plate"] = plate
        pool.append(c)
    del rec, Q
# stratified: per plate n/2; within a plate, half where the WRITTEN value changed (duration OFF != ON), half where only the join changed;
# each half split between gained stems and another stem (the old join removed)
def moved(c):
    return json.dumps(c["dur_off"], sort_keys=True) != json.dumps(c["dur_on"], sort_keys=True)
picks = []
plates = sorted({c["plate"] for c in pool})
for pl in plates:
    per = n // len(plates)
    for mv in (True, False):
        for kind in ("gained", "other_stem", "lost"):
            cs = [c for c in pool if c["plate"] == pl and moved(c) == mv and c["kind"] == kind]
            rng.shuffle(cs)
            picks += cs[:max(1, per // 4)]
picks = picks[:n]
rest = [c for c in pool if c not in picks]
rng.shuffle(rest)
picks += rest[:n - len(picks)]
rng.shuffle(picks)
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw, ImageFont
pages = {}
key = []
ims = []
for i, c in enumerate(picks):
    C = ctx[c["plate"]]
    g = c["glyph"]
    cell = "cell/" + "/".join(g.split("/")[1:5])
    det = (c["off_detail"] if c["kind"] == "lost" else c["on_detail"]) or {}
    sid = det.get("stem")
    if cell not in C["geo"] or sid not in C["stem_val"]:
        continue
    (rx0, ry0, rx1, ry1), up = C["geo"][cell]
    x, y, w, h = C["stem_val"][sid][:4]
    sb = [rx0 + x / up, ry0 + y / up, rx0 + (x + w) / up, ry0 + (y + h) / up]
    hb = C["gbox"].get(g) or sb
    cb = C["cellbox"].get(cell) or [sb[0] - 200, sb[1] - 100, sb[2] + 200, sb[3] + 100]
    pg = int(g.split("/")[1])
    if (c["plate"], pg) not in pages:
        pages[(c["plate"], pg)] = Image.fromarray(render_page(C["pdf"], pg, dpi=600).rgb).convert("RGB")
    im = pages[(c["plate"], pg)]
    sp = (cb[3] - cb[1]) / 10.0
    x0 = int(max(0, min(sb[0], hb[0]) - 4 * sp))
    x1 = int(min(im.width, max(sb[2], hb[2]) + 4 * sp))
    y0 = int(max(0, min(cb[1], sb[1], hb[1]) - 1 * sp))
    y1 = int(min(im.height, max(cb[3], sb[3], hb[3]) + 1 * sp))
    crop = im.crop((x0, y0, x1, y1))
    dr = ImageDraw.Draw(crop)
    dr.rectangle([sb[0] - x0 - 3, sb[1] - y0 - 3, sb[2] - x0 + 3, sb[3] - y0 + 3], outline=(255, 140, 0), width=2)
    name = "tile_%02d.png" % (len(key) + 1)
    crop.save(os.path.join(out, "tiles", name))
    ims.append(crop)
    key.append(dict(tile=len(key) + 1, plate=c["plate"], page=pg, glyph=g, change=c["kind"], off=c["off"], on=c["on"], dur_off=c["dur_off"], dur_on=c["dur_on"],
                    stem_box_page_px=[round(v, 1) for v in sb], crop_page_px=[x0, y0, x1, y1], page_reading=c.get("page_reading")))
json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1, default=str)
# numbered sheet
W = 4
th = [im.height for im in ims]
cw = 360
rows = [ims[i:i + W] for i in range(0, len(ims), W)]
sheet_h = 0
scaled = []
for r in rows:
    s = [im.resize((cw, max(1, int(im.height * cw / im.width)))) for im in r]
    scaled.append(s)
    sheet_h += max(x.height for x in s) + 30
sheet = Image.new("RGB", (W * (cw + 10), sheet_h), "white")
yy = 0
k = 1
dr = ImageDraw.Draw(sheet)
for s in scaled:
    for j, im in enumerate(s):
        sheet.paste(im, (j * (cw + 10), yy + 26))
        dr.text((j * (cw + 10) + 4, yy + 4), "Tile %d" % k, fill=(0, 0, 0))
        k += 1
    yy += max(x.height for x in s) + 30
sheet.save(os.path.join(out, "tiles", "sheet.png"))
print("tiles", len(key), dict(collections.Counter(k_["change"] for k_ in key)), "->", out)
