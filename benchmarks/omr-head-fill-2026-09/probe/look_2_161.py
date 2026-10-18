"""ROADMAP 2.161 -- look (for us, not a blind tile): the cell raster around each head of stems_<doc>.json, the detector's
box in RED, the record's accepted stems in GREEN, the runs the stem finder refused near the head in BLUE (label = refusal),
the erased raster beside it. One contact sheet per doc.
usage: look_2_161.py STEMS.json DOC SHEET.png [subject ...]"""
import collections
import json
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
SJ, DOC, SHEET = sys.argv[1:4]
ONLY = set(sys.argv[4:])
R = json.load(open(SJ))
sel = {s: r for s, r in R.items() if r.get("doc") == DOC and (s in ONLY or (not ONLY and not r["stems_attached"]))}
by_page = collections.defaultdict(list)
for s, r in sel.items():
    by_page[r["page"]].append(s)
tiles = []
for pg in sorted(by_page):
    (pws, cells), = prepare_pages(PDFS[DOC], [pg])
    for s in by_page[pg]:
        r = sel[s]
        sp = r["sp"]
        # find the cell again by the head's canonical box being inside it is ambiguous; use stored cell box via subject order
        cand = [c for c in cells if c.image is not None]
        # the probe saved no cell box; re-match by the page/system/staff/cell of the subject through staff order
        pi, si, st, ci = (int(v) for v in s.split("/")[1:5])
        from tools.omr.staged.gather import _system_local
        local = _system_local(pws.staves)
        cc = [c for c in cells if local.get(c.staff_index) == (si, st) and c.measure_index == ci]
        if len(cc) != 1:
            continue
        c = cc[0]
        img = c.image if c.image.ndim == 2 else c.image[..., 0]
        x, y, w, h = r["box"]
        x0, y0 = int(max(0, x - 3 * sp)), int(max(0, y - 5 * sp))
        x1, y1 = int(min(img.shape[1], x + w + 3 * sp)), int(min(img.shape[0], y + h + 5 * sp))
        im = Image.fromarray(np.ascontiguousarray(img[y0:y1, x0:x1])).convert("RGB")
        d = ImageDraw.Draw(im)
        for n in r["stems_near"]:
            bx, by, bw, bh = n["box"]
            d.rectangle([bx - x0, by - y0, bx + bw - x0, by + bh - y0], outline=(0, 170, 0), width=3)
        for n in r["refused_near"]:
            if n["outcome"] == "accepted":
                continue
            bx, by, bw, bh = n["box"]
            d.rectangle([bx - x0, by - y0, bx + bw - x0, by + bh - y0], outline=(0, 0, 255), width=2)
        d.rectangle([x - x0, y - y0, x + w - x0, y + h - y0], outline=(255, 0, 0), width=3)
        sc = 260.0 / im.height
        im = im.resize((max(1, int(im.width * sc)), 260))
        lab = Image.new("RGB", (max(im.width, 330), 300), "white")
        lab.paste(im, (0, 40))
        dd = ImageDraw.Draw(lab)
        dd.text((2, 2), "%s %s crops=%s" % (s, r["cause_2159"][:16], r.get("crops")), fill=(0, 0, 0))
        dd.text((2, 16), "; ".join("%s %.1f" % (n["outcome"][:14], n["h_sp"]) for n in r["refused_near"][:3]),
                fill=(0, 0, 200))
        tiles.append(lab)
cols = 4
W = max(t.width for t in tiles)
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (W * cols, 300 * rows), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * W, (i // cols) * 300))
sheet.save(SHEET)
print(len(tiles), "tiles ->", SHEET)
