"""2.278: review sheets for MY look (labelled, not for Sean). usage:
  sheet.py PLATE KIND DIAG.jsonl [CHORDS.json] N SEED OUTDIR
KIND = narrowed | chord. Writes OUTDIR/sample.json (the picked heads) and sheet_XX.png (8 crops per sheet, numbered)."""
import json, os, random, sys
import fitz
from PIL import Image, ImageDraw, ImageFont

PLATE, KIND, DIAG = sys.argv[1:4]
rest = sys.argv[4:]
CH = rest[0] if KIND == "chord" else None
N, SEED, OUT = int(rest[-3]), int(rest[-2]), rest[-1]
PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
PDF, SP = PDFS[PLATE]
doc = fitz.open(PDF)
rows = [json.loads(l) for l in open(DIAG)]
rng = random.Random(SEED)
if KIND == "narrowed":
    pool = [r for r in rows if r["fate"] == "duration_narrowed" and r.get("bbox")]
    pick = rng.sample(pool, min(N, len(pool)))
    items = [dict(sub=r["sub"], bbox=r["bbox"], reason=r.get("reason"), cands=r.get("cands"),
                  d={k: r["d"].get(k) for k in ("levels_certain", "levels_possible", "stems_attached", "beams_by_stem", "cv_beams", "yolo_beams", "yolo_kept",
                                                "beams_not_by_ink", "beams_far_side", "beams_neighbour_staff", "beam_side")},
                  bfs=(r.get("bfs") or {}).get("settled")) for r in pick]
else:
    G = json.load(open(CH))
    pick = rng.sample(G, min(N, len(G)))
    items = []
    for g in pick:
        hs = g["heads"]
        h = hs[0]
        bb = h["bbox_page"]
        items.append(dict(sub=str(h.get("glyph")), bbox=bb, reason="chord", cands=None,
                          d=dict(heads=[(x.get("stem_id") is not None, x["duration_type"], x["dots"], x["beam_levels"]) for x in hs]), bfs=None))
os.makedirs(OUT, exist_ok=True)
json.dump(items, open(os.path.join(OUT, "sample.json"), "w"), default=str)
BLUE = (31, 111, 235)
HW, HH = 6.0, 7.0
Z = 3.0 if PLATE == "litolff" else 1.7
tiles = []
for i, it in enumerate(items):
    s = it["sub"]
    bb = it["bbox"]
    pg = int(s.split("/")[1]) if s.startswith("glyph") else None
    if pg is None:
        pg = it.get("page")
    tiles.append((i, it))
# page index: diag rows keep it in sub; chord groups: take from the head's glyph id
def page_of(it):
    if it["sub"].startswith("glyph"): return int(it["sub"].split("/")[1])
    return it.get("page", 0)
font = ImageFont.load_default()
ims = []
for i, it in enumerate(items):
    bb = it["bbox"]
    if isinstance(bb, str):
        import ast
        bb = ast.literal_eval(bb)
        bb = [bb[0], bb[1], bb[0] + bb[2], bb[1] + bb[3]]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - HW * SP, cy - HH * SP, cx + HW * SP, cy + HH * SP)
    k = 72 / 600
    pgi = page_of(it)
    pix = doc[pgi].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (r[2] - r[0]), im.height / (r[3] - r[1])
    pad = 0.1 * SP
    box = [(bb[0] - pad - r[0]) * sx, (bb[1] - pad - r[1]) * sy, (bb[2] + pad - r[0]) * sx, (bb[3] + pad - r[1]) * sy]
    ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
    ImageDraw.Draw(im).text((4, 4), "#%d" % i, fill=(200, 0, 0), font=font)
    ims.append(im)
per = 8
for sidx in range(0, len(ims), per):
    chunk = ims[sidx:sidx + per]
    w, h = chunk[0].size
    sheet = Image.new("RGB", (4 * w + 5 * 6, 2 * h + 3 * 6), (255, 255, 255))
    for j, im in enumerate(chunk):
        sheet.paste(im, (6 + (j % 4) * (w + 6), 6 + (j // 4) * (h + 6)))
    sheet.save(os.path.join(OUT, "sheet_%02d.png" % (sidx // per)))
print("wrote", len(ims), "crops;", (len(ims) + per - 1) // per, "sheets in", OUT)
