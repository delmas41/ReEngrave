"""ROADMAP 2.159 -- one diagnosis crop per cause (for Sean and us, not a blind tile): the print around the head (x4), the
detector's box in RED, the located head box (if any) in GREEN, and to the right the BINARIZED raster inside the detector's
box (x10) -- what the 2.148 slit reader actually looked at -- with the numbers it measured.
usage: diag_crops_2_159.py OUTDIR PRINTDIR"""
import json
import os
import sys

sys.path.insert(0, ".")
import fitz  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
OUT, PR = sys.argv[1:3]
os.makedirs(PR, exist_ok=True)
CAUSES = json.load(open(os.path.join(OUT, "causes.json")))
PICK = [  # (file stem, doc, subject, what it shows)
    ("1-box-too-short-litolff", "litolff", "glyph/1/0/9/11/1",
     "detector box holds only the lower part of the head (0.89 sp tall < 0.9): the slit reader sees a rim, reads 0.00"),
    ("2-box-too-short-brahms", "brahms", None,
     "the same on Brahms (176 of 231): a part-boxed head"),
    ("3-box-too-tall-litolff", "litolff", "glyph/11/0/2/12/2",
     "detector box 2.07 sp tall (head + accidental/neighbour): not read at the first step"),
    ("4-box-too-wide-litolff", "litolff", "glyph/9/0/4/2/8",
     "detector box 1.91 sp wide (> 1.9): not read at the first step"),
    ("5-box-too-narrow-litolff", "litolff", "glyph/14/1/3/11/4",
     "detector box 1.06 sp wide (< 1.1, the key-flat guard): not read at the first step"),
    ("6-no-stem-attached-litolff", "litolff", "glyph/14/1/3/12/1",
     "head-sized, slit reads hollow (0.31) but no stem box touches the head box: 2.148 decides a half only on a stem"),
    ("7-slit-between-litolff", "litolff", "glyph/5/1/4/2/1",
     "head-sized, slit share 0.08: between solid (<=0.06) and hollow (>=0.18), so undecided (rule 8)"),
]
if True:   # the Brahms part-boxed example: the first too-short head with a stem and a located reading
    L = json.load(open(os.path.join(OUT, "located_brahms.json")))
    for r in CAUSES["brahms"]["rows"]:
        if r["cause"].startswith("box_too_short") and r["stems"] and r["subject"] in L \
                and L[r["subject"]]["iw"]["rows_share"] >= 0.18:
            PICK[1] = (PICK[1][0], "brahms", r["subject"], PICK[1][3])
            break
font = ImageFont.load_default()
key = []
pages = {}
for stem, doc, s, what in PICK:
    H = json.load(open(os.path.join(OUT, "heads_%s.json" % doc)))
    L = json.load(open(os.path.join(OUT, "located_%s.json" % doc)))
    h = H[s]
    row = next(r for r in CAUSES[doc]["rows"] if r["subject"] == s)
    bb = h["glyph_box"]["detail"]["bbox_page_px"]
    sp = L[s]["sp_page"] if s in L else h["space"] * (bb[2] - bb[0]) / h["glyph_box"]["value"][3]
    pad = 3.5 * sp
    r = (bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)
    k = 72 / 600
    pg = int(s.split("/")[1])
    pix = fitz.open(PDFS[doc])[pg].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72), clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    Z = 4
    im = im.resize((im.width * Z, im.height * Z), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle([(bb[0] - r[0]) * Z, (bb[1] - r[1]) * Z, (bb[2] - r[0]) * Z, (bb[3] - r[1]) * Z], outline=(220, 0, 0),
                width=2)
    if s in L:
        x, y, w, hh = L[s]["box_page"]
        d.rectangle([(x - r[0]) * Z, (y - r[1]) * Z, (x + w - r[0]) * Z, (y + hh - r[1]) * Z], outline=(0, 160, 0), width=2)
    if (doc, pg) not in pages:
        pages[(doc, pg)] = render_page(PDFS[doc], pg, dpi=600).binary
    B = pages[(doc, pg)]
    ins = B[int(round(bb[1])):int(round(bb[3])), int(round(bb[0])):int(round(bb[2]))]
    ins = Image.fromarray(np.where(ins == 0, 0, 255).astype(np.uint8)).convert("RGB")
    ins = ins.resize((ins.width * 10, ins.height * 10), Image.NEAREST)
    W = im.width + ins.width + 40
    Hh = max(im.height, ins.height) + 110
    sheet = Image.new("RGB", (W, Hh), "white")
    sheet.paste(im, (0, 100))
    sheet.paste(ins, (im.width + 30, 100))
    t = ImageDraw.Draw(sheet)
    loc = L.get(s)
    lines = ["2.159 %s  %s  %s" % (stem, doc, s), what,
             "measured: box %.2f x %.2f sp (head-sized %s), own stem %s, slit rows_share %s, hole %s, 2.23 centre ink %s"
             % (row["gate"][1], row["gate"][2], row["gate"][0], bool(row["stems"]), row["rows_share"], row["hole"],
                row["c23_raw"]),
             "located head box (green, %s): slit rows_share %s" % (loc["src"], loc["iw"]["rows_share"]) if loc
             else "no earlier reader located this head (no green box)",
             "RED = detector box; right = binarized pixels inside the red box (x10), what the slit reader read"]
    for i, ln in enumerate(lines):
        t.text((6, 6 + 18 * i), ln, fill=(0, 0, 0), font=font)
    fn = stem + ".png"
    sheet.save(os.path.join(PR, fn))
    key.append(dict(file=fn, doc=doc, subject=s, cause=row["cause"], measured=row, located=loc, page_box=bb))
    print(fn)
json.dump(key, open(os.path.join(PR, "index.json"), "w"), indent=1)
