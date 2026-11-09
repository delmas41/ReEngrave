"""2.280 micro test: 12 crops for Sean (out/print/2.280-micro/ + key.json). One staff; a thin BLUE box on the head, a thin ORANGE box on the stem arm B read
(none drawn where arm B abstained); the full stem in view. Question: "Is the boxed line this note's stem?" (abstained tiles: "Does this note have a stem, which side?").
Picks are rule-based and seeded (rng 280), fixed before the crops were looked at. usage: m4_crops.py OUTDIR"""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"),
        "brahms": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")}
R = {}
for p in PDFS:
    for s, r in json.load(open("out/2.280-micro/proto_%s.json" % p))["results"].items():
        r["plate"], r["sub"] = p, s
        R[p + ":" + s] = r
rng = random.Random(280)


def pick(n, pred):
    c = sorted(k for k, r in R.items() if pred(r))
    rng.shuffle(c)
    return c[:n]


f = lambda r: r["B"]["status"] == "filed"       # noqa: E731
real = lambda r: "real51" in r["groups"]        # noqa: E731
nn = lambda r: "notnote30" in r["groups"]       # noqa: E731
picks = []
for k in pick(2, lambda r: real(r) and f(r) and r["plate"] == "litolff" and r["B"]["kind"] == "single"):
    picks.append((k, "real head, arm B filed a single stem (Litolff)"))
for k in pick(1, lambda r: real(r) and f(r) and r["B"]["kind"] == "chord"):
    picks.append((k, "real head, arm B filed a chord-through stem"))
for k in pick(1, lambda r: real(r) and f(r) and r["plate"] == "brahms" and r["B"]["kind"] == "single"):
    picks.append((k, "real head, arm B filed a single stem (Brahms)"))
for k in pick(2, lambda r: real(r) and r["plate"] == "brahms" and r["B"].get("why") == "both_two_columns"):
    picks.append((k, "real head of a second, arm B abstained: both_two_columns"))
for k in pick(1, lambda r: real(r) and r["plate"] == "litolff" and r["B"].get("why") == "ruler_none"):
    picks.append((k, "real head, arm B abstained: ruler_none (Litolff)"))
for k in pick(2, lambda r: nn(r) and f(r)):
    picks.append((k, "NOT-NOTE control, arm B FILED a stem (false stem)"))
for k in pick(1, lambda r: nn(r) and r["label"] == "R" and not f(r)):
    picks.append((k, "NOT-NOTE control, whole-rest block, arm B abstained (correct)"))
for k in pick(1, lambda r: nn(r) and r["label"] == "N" and not f(r)):
    picks.append((k, "NOT-NOTE control, accidental/clef piece, arm B abstained (correct)"))
for k in pick(1, lambda r: "agree200" in r["groups"] and f(r) and r["row_boxes"] and
              r["B"]["direction"] != ("up" if (max(r["row_boxes"], key=lambda b: b[3] - b[1])[1] + max(r["row_boxes"], key=lambda b: b[3] - b[1])[3]) / 2 < (r["page_box"][1] + r["page_box"][3]) / 2 else "down")):
    picks.append((k, "head WITH a shipped stem row, arm B's direction DIFFERS from the row"))
rng.shuffle(picks)
print(len(picks), "picks")

docs, key = {}, {}
BLUE, ORANGE = (31, 111, 235), (255, 110, 0)
for n, (k, why) in enumerate(picks, 1):
    r = R[k]
    SP = r["sp"]
    doc = docs.setdefault(r["plate"], fitz.open(PDFS[r["plate"]]))
    x0, y0, x1, y1 = r["page_box"]
    B = r["B"]
    ys = [y0, y1] + ([B["box"][1], B["box"][3]] if B["status"] == "filed" else [])
    top, bot = min(ys) - 2.0 * SP, max(ys) + 2.0 * SP
    cy = (top + bot) / 2.0
    half = max(6.0 * SP, (bot - top) / 2.0)
    cx = (x0 + x1) / 2
    HW = 10.0
    clip = (cx - HW * SP, cy - half, cx + HW * SP, cy + half)
    Z = 900 / (2 * HW * SP)
    pg = r["page"]
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    d = ImageDraw.Draw(im)
    d.rectangle([(x0 - clip[0]) * sx, (y0 - clip[1]) * sy, (x1 - clip[0]) * sx, (y1 - clip[1]) * sy], outline=BLUE, width=1)
    if B["status"] == "filed":
        bx = B["box"]
        d.rectangle([(bx[0] - 1 - clip[0]) * sx, (bx[1] - clip[1]) * sy, (bx[2] + 1 - clip[0]) * sx, (bx[3] - clip[1]) * sy], outline=ORANGE, width=1)
    fn = "tile_%02d.png" % n
    im.save(os.path.join(OUT, fn))
    key[str(n)] = dict(file=fn, plate=r["plate"], subject=r["sub"], page=pg, why_picked=why, my_label=r["label"], armA_ruler=r["A_ship"],
                       armB=B, armB_noclaims=r["B_noclaims"]["status"], flipped=r["C_flip"]["status"], groups=r["groups"],
                       row_boxes=r["row_boxes"], head_page_box=r["page_box"], sp=SP)
json.dump(key, open(os.path.join(OUT, "key.json"), "w"), indent=1)
open(os.path.join(OUT, "README.md"), "w").write(
    "# 2.280 micro test crops\n\nOne staff. Thin BLUE box = the head. Thin ORANGE box = the stem the prototype (arm B: the shipped head ruler on unclaimed ink + chord-through rule) read; "
    "none where it abstained. Question: **Is the boxed (orange) line this note's stem?** Where nothing is drawn in orange: **Does the blue-boxed note have a stem, and on which side?** "
    "Includes not-note controls (rest blocks, accidental pieces) that should get no stem. Why each was picked and what the prototype said: key.json only.\n")
print("crops ->", OUT)
