"""2.280 blind tiles for Sean: "Does the boxed note have a stem, and which way does it go?"
One staff from the page (28 sp wide, head +-6 sp tall), ONE thin blue box = the head's detector box + 4 sp above and below, nothing else drawn.
10 stratum-A heads (narrowed, no touching stem row; my look labels in out/2.280/labels_*.json) + 2 controls (a clear stemmed black head; a clear stemmed half note), seeded order.
The bucket / label / expected answer live only in key.json.
usage: p9_tiles.py OUTDIR"""
import collections
import json
import os
import random
import sys
import fitz
from PIL import Image, ImageDraw

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
SL = LIB + "_shared-records/lane-report-slices-20261104-night/"
rng = random.Random(280)

picks = []


def add(plate, sub, kind, expect, extra=None):
    picks.append(dict(plate=plate, sub=sub, kind=kind, expect=expect, **(extra or {})))


def load(plate):
    R = json.load(open("out/2.280/rerunfull_%s.json" % plate))
    Bk = json.load(open("out/2.280/bucketsfull_%s.json" % plate))
    L = json.load(open("out/2.280/labels_%s.json" % plate))
    return R, Bk, L


def choose(plate, label, cause_prefix, n, extra_ok=lambda r: True):
    R, Bk, L = load(plate)
    c = sorted(s for s, lb in L.items() if lb == label and Bk[s]["cause"].startswith(cause_prefix) and extra_ok(R[s]))
    rng.shuffle(c)
    return c[:n]


for s in choose("litolff", "R", "0", 2):
    add("litolff", s, "A: Litolff rest block kept as a head", "not a note (a rest), no stem")
for pre in ("i   run REFUSED: WIDE", "ii", "i   ink run never"):
    for s in choose("litolff", "H", pre, 1):
        add("litolff", s, "A: Litolff real head in a clump (%s)" % pre.strip(), "a head with a stem fused into the clump (look)")
for s in choose("brahms", "D", "i   run REFUSED: WIDE", 3):
    add("brahms", s, "A: Brahms head of a second, stem on its partner", "a stem is on this head's pair (look)")
for s in choose("brahms", "S", "i   run REFUSED: TALL", 1):
    add("brahms", s, "A: Brahms single head, stem refused TALL", "a stem (look)")
for s in choose("brahms", "N", "ii", 1):
    add("brahms", s, "A: Brahms accidental boxed as a head", "not a note (a sharp/natural), no stem")

# controls from the slices: a whole note (decided written 4.0, hollow, no stem touching) and a clear stemmed head
for plate, ctl in (("litolff", "stemmed"), ("brahms", "half")):
    pop = json.load(open("out/2.280/pop_%s.json" % plate))
    val = {}
    for l in open(SL + plate + "/verdicts.jsonl"):
        v = json.loads(l)
        if v["quantity"] == "duration" and v["outcome"] == "decided":
            val[v["subject"]] = v["value"] or {}
    cand = []
    for r in pop:
        d = val.get(r["sub"], {})
        if ctl == "half" and r["n_phys"] == 1 and d.get("written") == 2.0 and r["cls"].startswith("noteheadHalf") and r["reach"] and \
                max(r["reach"].get("up_ext") or 0, r["reach"].get("down_ext") or 0) >= 2.5 and r["dur_reason"] == "head_and_marks":
            cand.append(r)
        if ctl == "stemmed" and r["n_phys"] == 1 and d.get("written") == 1.0 and r["cls"].startswith("noteheadBlack") and r["reach"] and \
                max(r["reach"].get("up_ext") or 0, r["reach"].get("down_ext") or 0) >= 2.5 and r["dur_reason"] == "head_and_marks":
            cand.append(r)
    rng.shuffle(cand)
    print(plate, ctl, "candidates", len(cand))
    if cand:
        add(plate, cand[0]["sub"], "control: " + ctl, "a stem, direction " + str((cand[0].get("reach") or {}).get("dir")) + " (record)")
rng.shuffle(picks)
print(len(picks), "picks")

docs = {}
key = {}
BLUE = (31, 111, 235)
HW, HH = 14.0, 6.0
for n, p in enumerate(picks, 1):
    pdf, SP = PDFS[p["plate"]]
    doc = docs.setdefault(p["plate"], fitz.open(pdf))
    rows = json.load(open("out/2.280/pop_%s.json" % p["plate"]))
    row = next(r for r in rows if r["sub"] == p["sub"])
    x0, y0, x1, y1 = row["page_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    clip = (cx - HW * SP, cy - HH * SP, cx + HW * SP, cy + HH * SP)
    Z = 1300 / (2 * HW * SP)
    k = 72 / 600
    pg = int(p["sub"].split("/")[1])
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * k for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    bx0, bx1 = x0 - 0.3 * SP, x1 + 0.3 * SP
    by0, by1 = y0 - 4.0 * SP, y1 + 4.0 * SP
    box = [(bx0 - clip[0]) * sx, (by0 - clip[1]) * sy, (bx1 - clip[0]) * sx, (by1 - clip[1]) * sy]
    ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
    fn = "tile_%02d.png" % n
    im.save(os.path.join(OUT, fn))
    key[str(n)] = dict(file=fn, page=pg, head_stem_reach=row.get("reach"), **p)
json.dump(key, open(os.path.join(OUT, "key.json"), "w"), indent=1)
open(os.path.join(OUT, "README.md"), "w").write(
    "# 2.280 blind tiles\n\nQuestion for every tile: **Does the boxed note have a stem, and which way does it go?** (up / down / no stem / not a note).\n"
    "One staff, one thin blue box (the head plus 4 staff spaces above and below), nothing else drawn. 12 tiles: 10 heads the reader gave a pitch and left with no stem row, "
    "plus 2 controls (a clear stemmed black head; a clear stemmed half note). Bucket and expected answer: key.json only.\n")
print("tiles ->", OUT)
