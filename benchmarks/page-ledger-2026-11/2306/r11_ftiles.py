"""2306 r11 blind tiles on what the FILE changes r9 -> r11 (both flag-ON pre-retire replays of their own full gathers): notes gained, lost, value
changed (value/dots, same pitch), drawn seeded and stratified (gained 4, lost 4, value 4, plates mixed). One staff per tile (its lines, the head's whole
stem and chord: 4.5 sp beyond the head each way, 2 sp round), ONE thin orange box on the note's head (its detector box). Numbered sheet; key outside.
Usage (cwd = tree): r11_ftiles.py OUTDIR KEY.json SEED plate:R9ON.json:R11ON.json:REC:PDF ..."""
import sys, os, json, re, random, collections
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw, ImageFont

out, keyp, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
specs = [a.split(":") for a in sys.argv[4:]]
os.makedirs(os.path.join(out, "tiles"), exist_ok=True)
rng = random.Random(seed)


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg") and h.get("kind") == "note":
            o[h["rg"]].append((h.get("pitch"), h.get("type"), len((h.get("sub") or {}).get("dot") or []), bool(h.get("blue"))))
    return o


pool = collections.defaultdict(list)
ctx = {}
#: bars (page/system/staff/cell) whose page stem reading changed r9 -> r11 -- a file change elsewhere is the two gathers' own variation (OCR claims), not this
#: round's; `CELLS` env names a json list per plate {plate: [cell keys]}
cells_ok = json.load(open(os.environ["CELLS"])) if os.environ.get("CELLS") else None
for plate, a, b, rec, pdf in specs:
    HA, HB = hosts(json.load(open(a))), hosts(json.load(open(b)))
    for g in set(HA) | set(HB):
        if cells_ok is not None and "/".join(g.split("/")[1:5]) not in set(cells_ok.get(plate, ())):
            continue
        x, y = sorted(HA.get(g, [])), sorted(HB.get(g, []))
        if x == y:
            continue
        if not x:
            k = "gained"
        elif not y:
            k = "lost"
        elif [t[:3] for t in x] != [t[:3] for t in y] and [t[0] for t in x] == [t[0] for t in y]:
            k = "value"
        else:
            continue
        pool[k].append(dict(plate=plate, glyph=g, change=k, r9_wrote=x, r11_wrote=y))
    ctx[plate] = (rec, pdf)
picks = []
for k, n in (("gained", 6), ("lost", 6), ("value", 4)):
    cand = sorted(pool[k], key=lambda t: (t["plate"], t["glyph"]))
    by = collections.defaultdict(list)
    for t in cand:
        by[t["plate"]].append(t)
    plates = sorted(by)
    i = 0
    while len([p for p in picks if p["change"] == k]) < n and any(by.values()):
        pl = plates[i % len(plates)]
        i += 1
        if by[pl]:
            picks.append(by[pl].pop(rng.randrange(len(by[pl]))))
rng.shuffle(picks)
info = {}
for plate, (rec, pdf) in ctx.items():
    txt = open(rec, encoding="utf-8").read()
    for t in picks:
        if t["plate"] != plate:
            continue
        g = t["glyph"]
        m = re.search(r'"subject":"%s","quantity":"glyph_box".{0,900}?"bbox_page_px":\[([^\]]*)\]' % re.escape(g), txt)
        st = "staff/" + "/".join(g.split("/")[1:4])
        m2 = re.search(r'"subject":"%s","quantity":"staff_lines","value":\[([^\]]*)\]' % re.escape(st), txt)
        info[g] = ([float(v) for v in m.group(1).split(",")], [float(v) for v in m2.group(1).split(",")])
    del txt
pages, key, thumbs = {}, [], []
for i, t in enumerate(picks, 1):
    rec, pdf = ctx[t["plate"]]
    p = int(t["glyph"].split("/")[1])
    if (t["plate"], p) not in pages:
        pages[(t["plate"], p)] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[(t["plate"], p)].copy()
    hb, lines = info[t["glyph"]]
    sp = (lines[-1] - lines[0]) / 4.0
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    top = min(lines[0] - sp, cy - 4.5 * sp) - 2 * sp
    bot = max(lines[-1] + sp, cy + 4.5 * sp) + 2 * sp
    ImageDraw.Draw(im).rectangle([hb[0] - 1, hb[1] - 1, hb[2] + 1, hb[3] + 1], outline=(255, 140, 0), width=1)
    tile = im.crop((int(cx - 6 * sp), int(top), int(cx + 6 * sp), int(bot)))
    tile = tile.resize((tile.width * 2, tile.height * 2), Image.LANCZOS)
    tile.save(os.path.join(out, "tiles", "tile%02d.png" % i))
    thumbs.append(tile)
    key.append(dict(tile=i, **t))
W, H = max(t.width for t in thumbs), max(t.height for t in thumbs)
cols = 4
sheet = Image.new("RGB", (cols * (W + 10), ((len(thumbs) + cols - 1) // cols) * (H + 40)), "white")
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
json.dump(dict(question="Is the boxed mark a note? If yes, what is its value (and is it dotted)?", seed=seed,
               pools={k: len(v) for k, v in pool.items()}, tiles=key), open(keyp, "w"), indent=1)
print({k: len(v) for k, v in pool.items()})
for k in key:
    print(k["tile"], k["plate"], k["glyph"], k["change"], k["r9_wrote"], "->", k["r11_wrote"])
