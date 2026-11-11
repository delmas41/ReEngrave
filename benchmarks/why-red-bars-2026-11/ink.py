"""2.291: UNCLAIMED INK INSIDE EACH NON-PLAIN BAR (claim_readout's own canvas, read-only).
usage: ink.py BARS.json PLATE OUT.json     -> per bar: components of unclaimed / contested / weak ink inside the bar's cell box and staff band
(staff band = top line -2.5 sp .. bottom line +2.5 sp), each with page box, ink px, size in staff spaces, the states it holds."""
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import cv2   # noqa: E402
import numpy as np   # noqa: E402

from tools.omr.staged import claim_readout as CR   # noqa: E402
from tools.omr.staged import lane_report as LR     # noqa: E402
from tools.omr.staged import cell_map as CM         # noqa: E402

bars = json.load(open(sys.argv[1]))
plate = sys.argv[2]
out = sys.argv[3]
pages = sorted({b["key"][0] for b in bars})
src = CR.resolve_source("%s:%s" % (plate, "20261029-night"))
rows = CR.read_rows(src, pages)
ed = CR.edition_info(rows)
pdf = LR.LIB / ed["edition_path"]
u = LR.PLATES[plate]["unit"]
res = {}
for pg in pages:
    canvas, verify, pws, cells = CR.build_page(rows, pdf, pg, CM.ROOT_DEFAULT, None)
    names = canvas.cat_names
    bad = [i for i, n in enumerate(names) if n.startswith(("unclaimed", "refused", "contested", "weak", "outside"))]
    m = np.isin(canvas.cat, bad) & canvas.ink
    print("page", pg, verify, flush=True)
    for b in bars:
        if b["key"][0] != pg:
            continue
        x0, _y0, x1, _y1 = [int(v) for v in b["cell_box"]]
        ys = b["staff_lines"]
        top, bot = int(min(ys) - 2.5 * u), int(max(ys) + 2.5 * u)
        sub = m[top:bot, x0:x1]
        comps = []
        if sub.any():
            n, lab, stats, _c = cv2.connectedComponentsWithStats(sub.astype(np.uint8), connectivity=8)
            for i in range(1, n):
                x, y, w, h, a = stats[i]
                if a < 30:
                    continue
                sl = (slice(y, y + h), slice(x, x + w))
                sel = sub[sl] & (lab[sl] == i)
                cats = collections.Counter(names[c] for c in canvas.cat[top:bot, x0:x1][sl][sel])
                comps.append({"box": [int(x0 + x), int(top + y), int(x0 + x + w), int(top + y + h)], "px": int(a), "w_sp": round(w / u, 2),
                              "h_sp": round(h / u, 2), "states": dict(cats.most_common(3))})
        comps.sort(key=lambda c: -c["px"])
        res["%d/%d/%d/%d" % tuple(b["key"])] = comps
    del canvas, pws, cells
json.dump(res, open(out, "w"))
print("wrote", out, len(res))
