"""2.247 r2: the strokes at ONE accidental place (re-cut cells; no detector, so no blocked heads): every stroke within 2 sp of the box,
its share in the box, kind, length, box (spaces from the box's top-left), touches; and the family reading with the flag on.
usage: place_probe.py PLATE PAGE X0 Y0 X1 Y1 CLASS"""
import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-accidental-family-2026-10")
os.environ["OMR_ACCIDENTAL_KIND"] = "1"
from tools.omr.staged import accidental_family as AF  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
from tools.omr.staged import pipeline  # noqa: E402
from tools.omr.staged import stroke_map as SM  # noqa: E402
import cause_cut as CC  # noqa: E402

plate, page = sys.argv[1], int(sys.argv[2])
bx0, by0, bx1, by1 = [float(v) for v in sys.argv[3:7]]
cls = sys.argv[7]
_pws, cells = pipeline.prepare_pages(CC.PDF[plate], [page], dpi=600)[0]
c = max(cells, key=lambda c: max(0, min(bx1, c.bbox_page_px[2]) - max(bx0, c.bbox_page_px[0])) * max(0, min(by1, c.bbox_page_px[3]) - max(by0, c.bbox_page_px[1])))
sp = G._cell_grid(c)[1] * 2.0
res = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
up, cb = c.upscale_factor, c.bbox_page_px
box = ((bx0 - cb[0]) * up, (by0 - cb[1]) * up, (bx1 - cb[0]) * up, (by1 - cb[1]) * up)
share = dict(SM.strokes_in_box(res, box))
for i, s in enumerate(res.strokes):
    x, y, w, h = s.box
    if x > box[2] + 2 * sp or x + w < box[0] - 2 * sp or y > box[3] + 2 * sp or y + h < box[1] - 2 * sp:
        continue
    print(i, s.kind, "share %.2f" % share.get(i, 0), "len", s.length_sp, "at", [round((x - box[0]) / sp, 2), round((y - box[1]) / sp, 2), round(w / sp, 2), round(h / sp, 2)],
          "touches", s.touches, "parts", len(getattr(s, "parts", []) or []))
fam = AF.family_row(cls, box, res.strokes, SM.strokes_in_box(res, box), sp)
print("box sp", round((box[2] - box[0]) / sp, 2), round((box[3] - box[1]) / sp, 2), "->", fam["type"], fam["why"], fam["members"], fam["features"])
