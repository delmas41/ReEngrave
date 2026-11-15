"""2306 r10 blind tiles: heads the page stem reader read NO stroke for although a vertical lies near (r10_near dumps, reproduced offline), drawn
seeded and stratified by plate x first failing test. One staff per tile (its five lines plus the head's stem, 3 spaces round both), ONE thin orange
box on the HEAD only (its detector box), nothing else of ours drawn. Numbered sheet; key outside the tile folder.
Usage (cwd = tree): r10_tiles.py OUTDIR KEY.json SEED plate:DUMP:REC:PDF ..."""
import sys, os, json, re, random, collections
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw, ImageFont

out, keyp, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
specs = [a.split(":") for a in sys.argv[4:]]
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
rng = random.Random(seed)
QUOTA = {("litolff", "head_end_too_far"): 3, ("litolff", "x_in"): 3, ("litolff", "x_out"): 2, ("brahms", "x_out"): 2, ("brahms", "x_in"): 1,
         ("brahms", "other"): 1}


def ff(r):
    b = r.get("nearest")
    if not b:
        return "other"
    ks = [k for k, m in b["fails"]]
    if "x_off_edge" in ks:
        return "x_in" if b["dx_out"] < 0 else "x_out"
    return ks[0] if ks and ks[0] == "head_end_too_far" else "other"


picks = []
ctx = {}
for plate, dump, rec, pdf in specs:
    rows = [r for r in json.load(open(dump)) if r.get("offline") == "no_stroke"]
    by = collections.defaultdict(list)
    for r in rows:
        by[ff(r)].append(r)
    for cls in sorted(by):
        k = QUOTA.get((plate, cls), 0)
        for r in rng.sample(sorted(by[cls], key=lambda r: r["g"]), min(k, len(by[cls]))):
            picks.append(dict(r, plate=plate, cls=cls))
    ctx[plate] = (rec, pdf)
rng.shuffle(picks)
need = collections.defaultdict(set)
for t in picks:
    need[t["plate"]].add(t["g"])
info = {}
for plate, (rec, pdf) in ctx.items():
    txt = open(rec, encoding="utf-8").read()
    for g in need[plate]:
        m = re.search(r'"subject":"%s","quantity":"glyph_box".{0,900}?"bbox_page_px":\[([^\]]*)\]' % re.escape(g), txt)
        st = "staff/" + "/".join(g.split("/")[1:4])
        m2 = re.search(r'"subject":"%s","quantity":"staff_lines","value":\[([^\]]*)\]' % re.escape(st), txt)
        info[g] = ([float(v) for v in m.group(1).split(",")], [float(v) for v in m2.group(1).split(",")])
    del txt
pages = {}
key = []
thumbs = []
for i, t in enumerate(picks, 1):
    rec, pdf = ctx[t["plate"]]
    p = int(t["g"].split("/")[1])
    if (t["plate"], p) not in pages:
        pages[(t["plate"], p)] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[(t["plate"], p)].copy()
    hb, lines = info[t["g"]]
    sp = (lines[-1] - lines[0]) / 4.0
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    top = min(lines[0] - sp, cy - 4.0 * sp) - 2 * sp
    bot = max(lines[-1] + sp, cy + 4.0 * sp) + 2 * sp
    box = [hb[0] - 1, hb[1] - 1, hb[2] + 1, hb[3] + 1]
    ImageDraw.Draw(im).rectangle(box, outline=(255, 140, 0), width=1)
    tile = im.crop((int(cx - 6 * sp), int(top), int(cx + 6 * sp), int(bot)))
    tile = tile.resize((tile.width * 2, tile.height * 2), Image.LANCZOS)
    tile.save(os.path.join(out, "tiles", "tile%02d.png" % i))
    thumbs.append(tile)
    key.append(dict(tile=i, plate=t["plate"], page=p, glyph=t["g"], first_failing_test=t["cls"], hollow=t.get("hollow"), ledger=t.get("ledger"),
                    chord=t.get("chord"), oval=t.get("oval"), old_join_direction=t.get("old_dir"), nearest=t.get("nearest"),
                    head_box_page_px=[round(v, 1) for v in hb]))
# numbered sheet, 4 across
W = max(t.width for t in thumbs)
H = max(t.height for t in thumbs)
cols = 4
rows_n = (len(thumbs) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (W + 10), rows_n * (H + 40)), "white")
dr = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
except Exception:
    font = None
for i, t in enumerate(thumbs):
    x, y = (i % cols) * (W + 10), (i // cols) * (H + 40)
    dr.text((x + 4, y + 4), str(i + 1), fill=(0, 0, 0), font=font)
    sheet.paste(t, (x, y + 36))
sheet.save(os.path.join(out, "sheet.png"))
json.dump(dict(question="Does the boxed note have a stem? If yes, does it go up or down from the head?", seed=seed, tiles=key), open(keyp, "w"), indent=1)
print(len(key), "tiles ->", out, "key", keyp)
for k in key:
    print(k["tile"], k["plate"], k["glyph"], k["first_failing_test"], "hollow" if k["hollow"] else "filled", "ledger" if k["ledger"] else "staff",
          "chord" if k["chord"] else "single", k["old_join_direction"])
