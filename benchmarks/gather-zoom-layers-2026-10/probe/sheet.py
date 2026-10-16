"""2.152 -- contact sheet of boxes a context fact flags, for the manager's eye (NOT blind tiles: one blue box, a number and the
fact that flagged it). Not Sean's evidence; my own look at the print is labelled as such in FINDINGS.

usage: sheet.py DOC SET OUT.png N     SET = hs (S1h or S2b flagged, kept head/rest) | p1 (P1 page z>6) | held (P1 z>6 in a held bar)
"""
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, __file__.rsplit("/", 1)[0])
sys.path.insert(0, ".")
import ctx  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

PDFS = {"brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf"}
doc, which, out, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
D = ctx.Doc("tmp_2152/%s.pkl" % doc)
kept = [g for g, r in D.glyph.items() if r["kept"] and r["cat"] in ("notehead", "rest")]
pick = []
for g in kept:
    if which == "hs":
        if D.s1(g)["h"] or (D.s2(g, 1.5) or {}).get("b"):
            pick.append((g, "S1h" if D.s1(g)["h"] else "S2b"))
    else:
        z = D.p1z(g)
        if z is not None and max(z[0], z[1]) > 6:
            pick.append((g, "P1 z=%.0f w%.2f h%.2f" % (max(z[0], z[1]), z[3], z[4])))
random.Random(2152).shuffle(pick)
pick = pick[:n]
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
except OSError:
    font = ImageFont.load_default()
pages = {}
tiles = []
for i, (g, why) in enumerate(pick, 1):
    r = D.glyph[g]
    if r["p"] not in pages:
        pages[r["p"]] = np.asarray(Image.fromarray(render_page(PDFS[doc], r["p"], dpi=600).rgb).convert("RGB"))
    a = pages[r["p"]]
    sp = r["sp"]
    x0b, y0b, x1b, y1b = r["bb"]
    x0, y0 = int(max(x0b - 9 * sp, 0)), int(max(y0b - 6 * sp, 0))
    x1, y1 = int(min(x1b + 9 * sp, a.shape[1])), int(min(y1b + 6 * sp, a.shape[0]))
    crop = Image.fromarray(a[y0:y1, x0:x1].copy())
    f = 420.0 / crop.width
    crop = crop.resize((420, int(crop.height * f)), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)
    dr.rectangle([(x0b - x0) * f - 3, (y0b - y0) * f - 3, (x1b - x0) * f + 3, (y1b - y0) * f + 3], outline=(31, 111, 235), width=3)
    t = Image.new("RGB", (420, crop.height + 30), "white")
    t.paste(crop, (0, 30))
    ImageDraw.Draw(t).text((4, 4), "%d %s  %s" % (i, g.replace("glyph/", ""), why), fill=(0, 0, 0), font=font)
    tiles.append(t)
cols = 3
rows = (len(tiles) + cols - 1) // cols
H = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * 424, rows * (H + 4)), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * 424, (i // cols) * (H + 4)))
sheet.save(out)
print(len(tiles), "->", out, [(g, w) for g, w in pick])
