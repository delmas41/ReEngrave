"""ROADMAP 2.161 -- one diagnosis crop per cause (for Sean and us; NOT a blind tile): the cell raster around the head,
RED = the detector's head box, GREEN = a stem the stem finder accepted (a `Q.STEM` row), BLUE = a vertical run the stem
finder refused (the refusal printed), with the cause and its counts on both plates in the header.
usage: diag_2_161.py W161DIR PRINTDIR"""
import json
import os
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.staged.gather import _system_local  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
W, PR = sys.argv[1:3]
os.makedirs(PR, exist_ok=True)
CA = json.load(open(os.path.join(W, "causes_2161.json")))
PICK = [  # (file stem, doc, subject, cause key, what it shows)
    ("1-stem-beside-box-litolff", "litolff", "glyph/14/1/3/12/1", "S1 stem_beside_box",
     "the stem was FOUND (green) 0.25 sp left of the box; the box stops short of the head's left tip, so no contact"),
    ("2-stem-refused-paired-litolff", "litolff", "glyph/11/0/1/9/2", "S2 refused:PAIRED",
     "two parallel verticals beside the head are dropped as an accidental's two strokes (the pair rule); one of them may be the stem"),
    ("3-stem-refused-tall-litolff", "litolff", "glyph/6/1/7/10/10", "S2 refused:TALL",
     "the stem runs on into other vertical ink (> 8 sp) and is refused as a barline"),
    ("4-stem-refused-wide-litolff", "litolff", "glyph/5/1/0/12/6", "S2 refused:WIDE",
     "the stem is fused with heads / ledger ink into one run wider than 0.6 sp"),
    ("5-stem-refused-short-litolff", "litolff", "glyph/5/0/7/0/7", "S2 refused:SHORT",
     "the run beside the head is shorter than 2 sp"),
    ("6-stem-refused-edge-litolff", "litolff", "glyph/6/1/4/8/9", "S2 refused:EDGE",
     "the stem stands within 0.8 sp of the cell edge (the barline filter)"),
    ("7-stem-off-box-vertically-litolff", "litolff", "glyph/15/0/0/2/2", "S1v stem_off_box_vertically",
     "the stem stands 0.35 sp above a box that holds only the lower part of the head"),
    ("8-no-stem-ink-litolff", "litolff", "glyph/6/0/0/9/1", "S3 no_stem_ink",
     "no vertical ink beside the box at all (by eye not a half note)"),
    ("9-brahms-key-accidental-wide", "brahms", "glyph/6/0/3/5/17", "S2 refused:WIDE",
     "Brahms: the 'notes' without a stem are mostly not notes (here a key-signature flat boxed as a head)"),
    ("10-stem-beside-box-brahms", "brahms", "glyph/2/0/13/3/1", "S1 stem_beside_box",
     "Brahms: the one real note -- the stem found 0.14 sp right of the box (a flagged note, not a half)"),
]
stems = {d: json.load(open(os.path.join(W, "stems_%s.json" % d))) for d in ("litolff", "brahms")}
cache = {}
idx = []
for stem_name, doc, s, key, what in PICK:
    r = stems[doc][s]
    pg = r["page"]
    if (doc, pg) not in cache:
        cache[(doc, pg)] = prepare_pages(PDFS[doc], [pg])[0]
    pws, cells = cache[(doc, pg)]
    local = _system_local(pws.staves)
    _, si, st, ci = (int(v) for v in s.split("/")[1:5])
    c = [c for c in cells if local.get(c.staff_index) == (si, st) and c.measure_index == ci][0]
    img = c.image if c.image.ndim == 2 else c.image[..., 0]
    sp = r["sp"]
    x, y, w, h = r["box"]
    x0, y0 = int(max(0, x - 3 * sp)), int(max(0, y - 5 * sp))
    x1, y1 = int(min(img.shape[1], x + w + 3 * sp)), int(min(img.shape[0], y + h + 5 * sp))
    im = Image.fromarray(np.ascontiguousarray(img[y0:y1, x0:x1])).convert("RGB")
    d = ImageDraw.Draw(im)
    for n in r["stems_near"]:
        bx, by, bw, bh = n["box"]
        d.rectangle([bx - x0, by - y0, bx + bw - x0, by + bh - y0], outline=(0, 170, 0), width=4)
    for n in r["refused_near"]:
        if n["outcome"] != "accepted":
            bx, by, bw, bh = n["box"]
            d.rectangle([bx - x0, by - y0, bx + bw - x0, by + bh - y0], outline=(0, 0, 255), width=3)
    d.rectangle([x - x0, y - y0, x + w - x0, y + h - y0], outline=(255, 0, 0), width=4)
    sc = 520.0 / im.height
    im = im.resize((max(1, int(im.width * sc)), 520))
    n_l = CA["litolff"]["stem"].get(key, 0)
    n_b = CA["brahms"]["stem"].get(key, 0)
    lines = ["2.161 %s  %s %s" % (stem_name, doc, s),
             "cause %s: Litolff %d, Brahms %d (of the heads with no stem: 32 / 10)" % (key, n_l, n_b),
             what,
             "box %.2f x %.2f sp; refused runs near: %s" % (r["w_sp"], r["h_sp"], "; ".join(
                 "%s %.1f sp" % (n["outcome"][:24], n["h_sp"]) for n in r["refused_near"][:2]) or "none"),
             "RED = detector head box   GREEN = stem the finder accepted   BLUE = vertical run the finder refused"]
    out = Image.new("RGB", (max(im.width, 900), 520 + 18 * len(lines) + 10), "white")
    dd = ImageDraw.Draw(out)
    for i, t in enumerate(lines):
        dd.text((4, 4 + 18 * i), t, fill=(0, 0, 0))
    out.paste(im, (0, 18 * len(lines) + 10))
    out.save(os.path.join(PR, stem_name + ".png"))
    idx.append(dict(file=stem_name + ".png", doc=doc, subject=s, cause=key, litolff=n_l, brahms=n_b, shows=what))
json.dump(idx, open(os.path.join(PR, "index.json"), "w"), indent=1)
print(len(idx), "crops ->", PR)
