"""2.170 diagnostic sheet (OURS DRAWN -- for the lane's eyes, never a tile): a seeded sample of narrowed-beam heads.
BLUE head box; GREEN every CV stem of the cell; RED the strokes the verdict refused (label = why); ORANGE other strokes of the cell.
usage: sheet_2_170.py DOC EX.json CELLS.json OUTDIR N SEED [FILTER]   FILTER: nostem|stem|all"""
import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                   "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                  "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
doc, exf, cf, outd, n, seed = sys.argv[1:7]
flt = sys.argv[7] if len(sys.argv) > 7 else "all"
ex = json.load(open(exf))
cells = json.load(open(cf))["rows"]
subs = sorted(ex["narrowed"])
if flt != "all":
    subs = [s for s in subs if bool((ex["narrowed"][s]["detail"] or {}).get("stems_attached")) == (flt == "stem")]
rnd = random.Random(int(seed))
rnd.shuffle(subs)
subs = subs[:int(n)]
out = Path(outd)
out.mkdir(parents=True, exist_ok=True)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
pages = {}
index = []
for i, s in enumerate(sorted(subs, key=lambda x: [int(v) for v in x.split("/")[1:]])):
    ck = "cell/" + "/".join(s.split("/")[1:5])
    rows = cells.get(ck, [])
    cb = next(o["value"] for o in rows if o["quantity"] == "cell_box")
    g = next(o for o in rows if o["quantity"] == "glyph_box" and o["subject"] == s and o["_kind"] == "obs")
    gb = g["detail"]["bbox_page_px"]
    sc = g["value"][3] / max(gb[2] - gb[0], 1e-6)          # canonical px per page px

    def page(v):
        x, y, w, h = v
        return (cb[0] + x / sc, cb[1] + y / sc, cb[0] + (x + w) / sc, cb[1] + (y + h) / sc)
    pg = int(s.split("/")[1])
    if pg not in pages:
        pages[pg] = np.asarray(Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB"))
    a = pages[pg]
    sp = 100.0 / sc
    x0, y0 = int(max(gb[0] - 6 * sp, 0)), int(max(gb[1] - 8 * sp, 0))
    x1, y1 = int(min(gb[2] + 6 * sp, a.shape[1])), int(min(gb[3] + 8 * sp, a.shape[0]))
    k = 2.0 if sp < 25 else 1.2
    im = Image.fromarray(a[y0:y1, x0:x1].copy()).resize((int((x1 - x0) * k), int((y1 - y0) * k)), Image.LANCZOS)
    d = ImageDraw.Draw(im)

    def rect(b, col, w=2):
        d.rectangle([(b[0] - x0) * k, (b[1] - y0) * k, (b[2] - x0) * k, (b[3] - y0) * k], outline=col, width=w)
    det = ex["narrowed"][s]["detail"] or {}
    refused = {r["id"]: r["why"] for r in det.get("refused_strokes") or []}
    for o in rows:
        if o["_kind"] != "obs":
            continue
        if o["quantity"] == "stem":
            rect(page(o["value"]), (0, 170, 0), 2)
        elif o["quantity"] == "beam_stroke":
            col = (220, 0, 0) if o["id"] in refused else (255, 140, 0)
            b = page(o["value"])
            rect(b, col, 2)
            if o["id"] in refused:
                d.text(((b[0] - x0) * k, (b[1] - y0) * k - 22), refused[o["id"]] + " " + (o.get("reader") or "")[:3],
                       fill=col, font=font)
    rect(gb, (31, 111, 235), 3)
    lab = "%d %s %s st=%s" % (i + 1, s, ex["narrowed"][s]["reason"][:12], det.get("stems_attached"))
    t = Image.new("RGB", (max(im.width, 700), im.height + 30), "white")
    t.paste(im, (0, 30))
    ImageDraw.Draw(t).text((4, 4), lab, fill=(0, 0, 0), font=font)
    t.save(out / ("s%02d.png" % (i + 1)))
    index.append(dict(n=i + 1, glyph=s, refused=refused, stems_attached=det.get("stems_attached"),
                      cands=[c["value"]["written"] for c in ex["narrowed"][s]["candidates"] or []]))
json.dump(index, open(out / "index.json", "w"), indent=1)
print("wrote", len(index))
