"""ROADMAP 2.304: where does the owned-ink mask fall in a window? A look, not evidence.

    OMR_TEXT_CROP_OWNED_INK=1 python3 benchmarks/text-reader-owned-ink-2026-11/mask_debug.py PDF PAGE OUT.png x0,y0,x1,y1
Writes the window with the owned pixels painted red (ink kept black).
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from tools.omr.staged import barline_columns as BC  # noqa: E402
from tools.omr.staged import owned_ink as OI  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

pdf, page, out, spec = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
((pws, cells),) = prepare_pages(pdf, [page], dpi=600)
oi = OI.attach(pws)
x0, y0, x1, y1 = (int(v) for v in spec.split(","))
for c in BC.fit_columns(pws):
    if c["y0"] <= y1 and c["y1"] >= y0:
        xa, xb = BC.x_at(c, y0), BC.x_at(c, y1)
        if x0 - 50 <= xa <= x1 + 50 or x0 - 50 <= xb <= x1 + 50:
            print("column", {k: c[k] for k in ("system", "x", "y0", "y1", "slope", "intercept", "staves")}, "x at window", round(xa, 1), round(xb, 1))
raw = oi.masks["barline"][y0:y1, x0:x1]
print("raw barline mask px in window", int(raw.sum()), "staff_line", int(oi.masks["staff_line"][y0:y1, x0:x1].sum()))
final = oi.mask((x0, y0, x1, y1), 15.75)
print("after give-back", 0 if final is None else int(final.sum()))
img = pws.page.rgb[y0:y1, x0:x1].copy()
vis = img.copy()
vis[raw] = (0, 200, 255)
if final is not None:
    vis[final] = (0, 0, 255)
cv2.imwrite(out, cv2.resize(np.hstack([img, vis]), None, fx=3, fy=3, interpolation=cv2.INTER_NEAREST))
