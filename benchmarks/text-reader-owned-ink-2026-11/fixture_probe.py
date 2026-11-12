"""ROADMAP 2.304: what the owned-ink mask does over the real-pixel fixture's two real candidate windows (a look)."""
import json
import os
import sys
import types

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from tools.omr.staged import owned_ink as OI  # noqa: E402

z = np.load(os.path.join(ROOT, "tools/omr/tests/data_text_crop_owned_ink_2_304.npz"), allow_pickle=False)
meta = json.loads(str(z["meta"]))
x0, y0, x1, y1 = meta["window"]
W = x1 - x0
rgb = z["rgb"]
bar = np.unpackbits(z["barline"], axis=1)[:, :W].astype(bool)
sl = np.unpackbits(z["staff_line"], axis=1)[:, :W].astype(bool)
print(rgb.shape, bar.sum(), sl.sum())
page = types.SimpleNamespace(rgb=rgb)
oi = OI.OwnedInk(page, {"barline": bar, "staff_line": sl}, ("barline",), 1, 2)
page.owned_ink = oi
sp = meta["spacing"]
for name, b in meta["boxes"].items():
    px, py = int(round(1.3 * sp)), int(round(0.45 * sp))
    r = (b[0] - px - x0, b[1] - py - y0, b[2] + px - x0, b[3] + py - y0)
    m = oi.mask(r, sp)
    print(name, r, None if m is None else int(m.sum()), "raw bar in rect", int(bar[r[1]:r[3], r[0]:r[2]].sum()))
    if m is not None:
        cols = np.nonzero(m.any(axis=0))[0] + r[0] + x0
        print(" page x with mask:", sorted(set(cols.tolist())))
