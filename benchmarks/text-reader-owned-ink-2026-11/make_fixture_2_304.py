"""ROADMAP 2.304: cut the test fixture `tools/omr/tests/data_text_crop_owned_ink_2_304.npz` from the REAL page (Litolff p8, the `sempre piu p` of bars 11-12, Sean 2026-11-11 2.301 r1
tile 4 / 2.303 part 1): the render's pixels of one window, the owner masks `owned_ink.attach` builds there (barline rule, staff lines), and the real candidate boxes.

    python3 benchmarks/text-reader-owned-ink-2026-11/make_fixture_2_304.py PDF
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.environ["OMR_TEXT_CROP_OWNED_INK"] = "1,staff_line"
from tools.omr.staged import owned_ink as OI  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

WIN = (1490, 640, 1860, 860)        # x0, y0, x1, y1: the word between staves 1-2 and 2-3 of the first system, its right barline, the thin rules through it
((pws, cells),) = prepare_pages(sys.argv[1], [8], dpi=600)
oi = OI.attach(pws)
x0, y0, x1, y1 = WIN
pk = lambda m: np.packbits(m[y0:y1, x0:x1].astype(np.uint8), axis=1)  # noqa: E731
sp = float(np.median([s.line_spacing_px for s in pws.staves]))
meta = dict(window=list(WIN), spacing=sp, boxes={"sempre_piu": [1510, 787, 1718, 822], "sempre_piu_p": [1570, 787, 1828, 822]})
np.savez_compressed(os.path.join(ROOT, "tools/omr/tests/data_text_crop_owned_ink_2_304.npz"),
                    rgb=pws.page.rgb[y0:y1, x0:x1], barline=pk(oi.masks["barline"]), staff_line=pk(oi.masks["staff_line"]), meta=json.dumps(meta))
print("wrote fixture; window", WIN, "sp", sp)
