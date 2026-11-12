"""ROADMAP 2.304: what the text reader is shown. For one page and some candidate boxes, writes the four crops the reader can get today (wide, tight, and each with the
2.254 r3 through-line retry) as one strip PNG per box -- a look, not evidence.

    python3 benchmarks/text-reader-owned-ink-2026-11/crops_cause.py PDF PAGE OUTDIR x0,y0,x1,y1 [...]
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import tools.omr.direction_text as DT  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

pdf, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
os.makedirs(out, exist_ok=True)
((pws, cells),) = prepare_pages(pdf, [page], dpi=600)
from tools.omr.staged import owned_ink as OI  # noqa: E402
if OI.enabled():
    OI.attach(pws)
for spec in sys.argv[4:]:
    box = tuple(int(v) for v in spec.split(","))
    cy = (box[1] + box[3]) / 2.0
    st = min(pws.staves, key=lambda s: abs((s.top_y + s.bottom_y) / 2.0 - cy))
    sp = float(st.line_spacing_px)
    cand = DT.TextCandidate(staff_index=st.staff_index, measure_index=0, bbox_page=box, placement="above", n_components=1)
    imgs = [DT.crop_for(pws.page, cand, sp), DT.crop_for(pws.page, cand, sp, lines=True),
            DT.tight_crop_for(pws.page, cand, sp), DT.tight_crop_for(pws.page, cand, sp, lines=True)]
    h = max(i.shape[0] for i in imgs)
    pad = [cv2.copyMakeBorder(i, 0, h - i.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(120, 120, 255)) for i in imgs]
    cv2.imwrite(os.path.join(out, "crop_%d_%d_%d_%d.png" % box), np.vstack([cv2.resize(p, (800, int(p.shape[0] * 800 / p.shape[1]))) for p in pad]))
    print(spec, "sp", sp)
