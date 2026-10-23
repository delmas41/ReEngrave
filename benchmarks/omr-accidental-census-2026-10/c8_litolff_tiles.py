"""2.197 C8: Litolff TYPE CHECK (my look, blind to the class). Draws N random accidental-/key-class boxes of the current-tree Litolff gather (stratified by
detector class, seed 2197) as neutral ORANGE-boxed tiles; the key (class, conf, what ADJUDICATE/EXPORT did) is written to a separate JSON.
usage: c8_litolff_tiles.py VIEW.json XML PDF OUTDIR"""
import sys, json, random, collections, pathlib, fitz
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, fam, kind, ALT
from PIL import Image, ImageDraw, ImageFont
view = View(sys.argv[1], sys.argv[2]); pdf = sys.argv[3]; out = pathlib.Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
UNIT = 15.75
rng = random.Random(2197)
pool = collections.defaultdict(list)
for pg, bs in view.boxes.items():
    for g in bs:
        if g["reader"] != "detector" or not fam(g["cls"]): continue
        key = ("key_cell0" if g["cell"] == 0 else "key_later") if fam(g["cls"]) == "key" else g["cls"]
        pool[key].append(g)
want = {"accidentalFlat": 10, "accidentalNatural": 12, "accidentalSharp": 8, "accidentalDoubleSharp": 3, "key_later": 6, "key_cell0": 3}
pick = []
for k, n in want.items():
    xs = sorted(pool[k], key=lambda g: g["key"]); rng.shuffle(xs); pick += [(k, g) for g in xs[:n]]
rng.shuffle(pick)
doc = fitz.open(pdf); cache = {}
font = ImageFont.load_default()
tiles, key = [], []
for i, (k, g) in enumerate(pick):
    pg = g["page"]
    if pg not in cache:
        pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY); cache[pg] = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    b = g["box"]; cx = (b[0] + b[2]) / 2; cy = (b[1] + b[3]) / 2
    a, t, c, d = int(cx - 6.5 * UNIT), int(cy - 5 * UNIT), int(cx + 6.5 * UNIT), int(cy + 5 * UNIT)
    SC = 3.0
    crop = cache[pg].crop((a, t, c, d)).resize((int((c - a) * SC), int((d - t) * SC)), Image.LANCZOS)
    dr = ImageDraw.Draw(crop); dr.rectangle([(b[0] - a) * SC, (b[1] - t) * SC, (b[2] - a) * SC, (b[3] - t) * SC], outline=(255, 140, 0), width=2)
    cv = Image.new("RGB", (crop.width, crop.height + 16), (255, 255, 255)); cv.paste(crop, (0, 16)); ImageDraw.Draw(cv).text((3, 2), "T%02d" % i, fill=(0, 0, 0), font=font)
    tiles.append(cv)
    row = view.accpos.get(g["key"]); own = view.verdict(g["key"], "accidental_owner"); dt = (row or {}).get("detail") or {}
    ent = dict(tile=i, stratum=k, key=g["key"], cls=g["cls"], conf=round(g["conf"] or 0, 3), page=pg, cell=g["cell"], box=b,
               acc_row=bool(row), alteration=dt.get("alteration"), absorbed=bool(dt.get("one_ink_absorbed")),
               one_ink_winner=(dt.get("one_ink") or {}).get("winner"), one_ink_rivals=(dt.get("one_ink") or {}).get("rivals"),
               owner=(own["outcome"], own["reason"], own.get("value")) if own else None)
    if own and own["outcome"] == "decided":
        xn = view.xml_notes.get(own["value"]); ent["xml"] = xn
    key.append(ent)
PER = 8
for s in range(0, len(tiles), PER):
    grp = tiles[s:s + PER]; W = max(t.width for t in grp); rows = [grp[j:j + 2] for j in range(0, len(grp), 2)]
    H = sum(max(t.height for t in r) + 4 for r in rows)
    sh = Image.new("RGB", (W * 2 + 4, H), (255, 255, 255)); y = 0
    for r in rows:
        x = 0
        for t in r: sh.paste(t, (x, y)); x += W + 4
        y += max(t.height for t in r) + 4
    sh.save(out / ("litolff_tiles%d.png" % (s // PER)))
json.dump(key, open(out / "litolff_tiles_key.json", "w"), default=str)
print(len(tiles), "tiles", {k: len(v) for k, v in pool.items()})
