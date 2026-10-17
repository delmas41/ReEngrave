"""ROADMAP 2.161 -- cut the real-raster test fixture `tools/omr/tests/data_head_stem_bridge_2_161.npz` from Litolff pdf 14
(cells re-cut as production cuts them, erased raster): POS = crop 22 of litolff-unread-35 (`glyph/14/1/3/12/1`, a half whose
stem stands 0.25 sp left of its detector box), NEG = the first black head on the same page with a stem 0.05-0.35 sp beside
its box, rows overlapping, whose gap is NOT bridged (white between head and stem).
usage: fixture_2_161.py SLICEDIR"""
import collections
import json
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged.pipeline import prepare_pages  # noqa: E402
from tools.omr.staged.gather import _system_local, head_stem_bridge  # noqa: E402
from tools.omr.line_detection import _binary_ink  # noqa: E402
from tools.omr.staged.geometry import stem_touches_head  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
SD = sys.argv[1]
pws, cells = prepare_pages(PDF, [14])[0]
local = _system_local(pws.staves)
rows = collections.defaultdict(lambda: collections.defaultdict(list))
for line in open(SD + "/litolff/p14.observations.jsonl"):
    if '"glyph_box"' in line or '"stem"' in line:
        o = json.loads(line)
        s = o["subject"]
        ck = s if s.startswith("cell/") else "cell/" + s[6:].rsplit("/", 1)[0]
        rows[ck][o["quantity"]].append(o)


def cell_of(ck):
    _, p, si, st, ci = ck.split("/")
    return [c for c in cells if local.get(c.staff_index) == (int(si), int(st)) and c.measure_index == int(ci)][0]


def gray(img):
    return np.ascontiguousarray(img if img.ndim == 2 else img[..., 0])


out = {}
ck = "cell/14/1/3/12"
c = cell_of(ck)
stems = [tuple(o["value"]) for o in rows[ck]["stem"]]
hb = [o["value"][1:] for o in rows[ck]["glyph_box"] if o["subject"] == "glyph/14/1/3/12/1"][0]
print("pos full cell", head_stem_bridge(_binary_ink(c.image_no_staff), hb, stems, 100.0, []))
x0, y0 = int(hb[0] - 150), int(hb[1] - 400)
x1, y1 = int(hb[0] + hb[2] + 100), int(hb[1] + hb[3] + 400)
crop = gray(c.image_no_staff[y0:y1, x0:x1])
near = []
for s in stems:
    if s[0] < x1 and s[0] + s[2] > x0 and s[1] < y1 and s[1] + s[3] > y0:
        top, bot = max(s[1], y0), min(s[1] + s[3], y1)
        near.append([s[0] - x0, top - y0, s[2], bot - top])
out.update(pos_img=crop, pos_head=np.array([hb[0] - x0, hb[1] - y0, hb[2], hb[3]], float), pos_stems=np.array(near, float))
print("pos crop", head_stem_bridge(_binary_ink(crop), out["pos_head"], out["pos_stems"], 100.0, []))
found = None
for ck2, cr in sorted(rows.items()):
    stems2 = [tuple(o["value"]) for o in cr["stem"]]
    for o in cr["glyph_box"]:
        if found or not str(o["value"][0]).startswith("noteheadBlack"):
            continue
        b = o["value"][1:]
        if any(stem_touches_head(s, b) for s in stems2):
            continue
        for s in stems2:
            gap = max(s[0] - (b[0] + b[2]), b[0] - (s[0] + s[2]))
            if 5 < gap <= 35 and s[1] < b[1] + b[3] and s[1] + s[3] > b[1]:
                c2 = cell_of(ck2)
                if head_stem_bridge(_binary_ink(c2.image_no_staff), b, [s], 100.0, []) is None:
                    found = (o["subject"], b, s, c2)
                    break
sub2, b, s, c2 = found
x0, y0 = int(min(b[0], s[0]) - 60), int(min(b[1], s[1]) - 60)
x1, y1 = int(max(b[0] + b[2], s[0] + s[2]) + 60), int(max(b[1] + b[3], s[1] + s[3]) + 60)
out.update(neg_img=gray(c2.image_no_staff[y0:y1, x0:x1]),
           neg_head=np.array([b[0] - x0, b[1] - y0, b[2], b[3]], float),
           neg_stems=np.array([[s[0] - x0, s[1] - y0, s[2], s[3]]], float))
print("neg", sub2, b, s, head_stem_bridge(_binary_ink(out["neg_img"]), out["neg_head"], out["neg_stems"], 100.0, []))
np.savez_compressed("tools/omr/tests/data_head_stem_bridge_2_161.npz", **out)
print("written; pos", out["pos_img"].shape, "neg", out["neg_img"].shape)
