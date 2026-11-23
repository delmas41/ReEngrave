"""2306 r4 blind tiles on what the WRITTEN FILE changes under OMR_PAGE_STEMS (flag OFF vs ON, from diag_replay's two arms): notes lost, gained,
value moved, voice moved; plus places in Litolff's own-head-direction red bars. One staff (the cell's crop), ONE thin orange box over the changed
note(s), the crop grown to hold the whole stem the page read for them (Q.PAGE_STEM stem_box) and the chord. Numbered sheet; key outside the folder.
Usage: file_tiles.py OUT SEED plate:PREFIX:REC:PDF[:dirbars] ..."""
import sys, os, json, random, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw

out, seed = sys.argv[1], int(sys.argv[2])
rng = random.Random(seed)
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
pool = []
ctx = {}
for spec in sys.argv[3:]:
    parts = spec.split(":")
    plate, pre, rp, pdf = parts[:4]
    dirbars = set(tuple(int(x) for x in b.split("/")) for b in (parts[4].split(",") if len(parts) > 4 and parts[4] else []))
    rec = load_record(rp)["record"]
    boxes = LR.glyph_boxes(rec["observations"])
    cellbox = {o["subject"]: o["value"] for o in rec["observations"] if o["quantity"] == "cell_box"}
    pstem = {o["subject"]: (o.get("detail") or {}).get("stem_box") for o in rec["observations"] if o["quantity"] == "page_stem"}
    ctx[plate] = dict(boxes=boxes, cellbox=cellbox, pstem=pstem, pdf=pdf)
    A = json.load(open(pre + ".off.json"))
    B = json.load(open(pre + ".on.json"))

    def hosts(D):
        o = collections.defaultdict(list)
        for h in D["hosts"]:
            if h.get("rg") and h.get("kind") == "note":
                o[h["rg"]].append(h)
        return o
    HA, HB = hosts(A), hosts(B)
    for rg in set(HA) | set(HB):
        a, b = HA.get(rg, []), HB.get(rg, [])
        bar = tuple(int(x) for x in rg.split("/")[1:5])
        if not a:
            k = "gained"
        elif not b:
            k = "lost"
        elif sorted(h.get("type") or "" for h in a) != sorted(h.get("type") or "" for h in b):
            k = "value"
        elif sorted(str(h.get("voice")) for h in a) != sorted(str(h.get("voice")) for h in b):
            k = "voice"
        else:
            continue
        desc = lambda hs: [(h.get("pitch"), h.get("type"), "v%s" % h.get("voice")) for h in hs]
        pool.append(dict(plate=plate, rg=rg, kind=k, bar=bar, off=desc(a), on=desc(b), dirbar=bar in dirbars))
want = [("lost", 4), ("gained", 2), ("value", 2), ("voice", 2)]
picks = []
dirs = [c for c in pool if c["dirbar"] and c["plate"] == "litolff"]
rng.shuffle(dirs)
seen_bars = set()
for c in dirs:
    if c["bar"] not in seen_bars and len([p for p in picks if p["dirbar"]]) < 2:
        picks.append(c)
        seen_bars.add(c["bar"])
for k, n in want:
    cs = [c for c in pool if c["kind"] == k and c["bar"] not in seen_bars]
    rng.shuffle(cs)
    # alternate plates
    by = collections.defaultdict(list)
    for c in cs:
        by[c["plate"]].append(c)
    got = 0
    while got < n and any(by.values()):
        for pl in sorted(by):
            if by[pl] and got < n:
                c = by[pl].pop(0)
                if c["bar"] in seen_bars:
                    continue
                picks.append(c)
                seen_bars.add(c["bar"])
                got += 1
rng.shuffle(picks)
pages = {}
key, ims = [], []
for c in picks:
    C = ctx[c["plate"]]
    b = C["boxes"].get(c["rg"])
    if not b:
        continue
    hb = b["box"]
    cell = "cell/" + "/".join(c["rg"].split("/")[1:5])
    cb = C["cellbox"].get(cell) or [hb[0] - 200, hb[1] - 150, hb[2] + 200, hb[3] + 150]
    sb = C["pstem"].get(c["rg"]) or hb
    p = int(c["rg"].split("/")[1])
    if (c["plate"], p) not in pages:
        pages[(c["plate"], p)] = Image.fromarray(render_page(C["pdf"], p, dpi=600).rgb).convert("RGB")
    im = pages[(c["plate"], p)]
    sp = (cb[3] - cb[1]) / 10.0
    x0 = int(max(0, min(hb[0], sb[0]) - 5 * sp)); x1 = int(min(im.width, max(hb[2], sb[2]) + 5 * sp))
    y0 = int(max(0, min(cb[1], sb[1], hb[1]) - sp)); y1 = int(min(im.height, max(cb[3], sb[3], hb[3]) + sp))
    crop = im.crop((x0, y0, x1, y1))
    dr = ImageDraw.Draw(crop)
    dr.rectangle([hb[0] - x0 - 3, hb[1] - y0 - 3, hb[2] - x0 + 3, hb[3] - y0 + 3], outline=(255, 140, 0), width=2)
    n = len(key) + 1
    crop.save(os.path.join(out, "tiles", "tile_%02d.png" % n))
    ims.append(crop)
    key.append(dict(tile=n, plate=c["plate"], page=p, glyph=c["rg"], change=c["kind"], off_wrote=c["off"], on_wrote=c["on"],
                    in_own_head_direction_red_bar=c["dirbar"], crop_page_px=[x0, y0, x1, y1], box_page_px=[round(v, 1) for v in hb]))
json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1, default=str)
cw = 320
rows = [ims[i:i + 4] for i in range(0, len(ims), 4)]
scaled = [[x.resize((cw, max(1, int(x.height * cw / x.width)))) for x in r] for r in rows]
H = sum(max(x.height for x in r) + 30 for r in scaled)
sheet = Image.new("RGB", (4 * (cw + 10), H), "white")
d = ImageDraw.Draw(sheet)
y, k = 0, 1
for r in scaled:
    for j, x in enumerate(r):
        sheet.paste(x, (j * (cw + 10), y + 26))
        d.text((j * (cw + 10) + 4, y + 6), "Tile %d" % k, fill=(0, 0, 0))
        k += 1
    y += max(x.height for x in r) + 30
sheet.save(os.path.join(out, "tiles", "sheet.png"))
print("tiles", len(key), collections.Counter(t["change"] for t in key), "dirbar", sum(t["in_own_head_direction_red_bar"] for t in key))
