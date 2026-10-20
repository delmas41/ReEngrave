"""usage: crop_wholes.py MINI_RECORD.json PDF OUT_DIR TAG WHOLES.json [N] -- print crops (nothing of ours drawn) of the whole notes the
OFF arm wrote (`.wholes.json`), around each glyph's own page box (600 dpi, shown x2). Reads boxes from the mini record rerun_whole.py wrote."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

rec, pdf, out, tag, wj = sys.argv[1], sys.argv[2], Path(sys.argv[3]), sys.argv[4], sys.argv[5]
n_max = int(sys.argv[6]) if len(sys.argv) > 6 else 12
out.mkdir(parents=True, exist_ok=True)
boxes = {o["subject"]: o["detail"]["bbox_page_px"] for o in json.load(open(rec))["observations"]}
pages = {}
for k, w in enumerate(json.load(open(wj))[:n_max], 1):
    g = w["glyph"]
    x0_, y0_, x1_, y1_ = boxes[g]
    x, y, bw, bh = x0_, y0_, x1_ - x0_, y1_ - y0_
    page = int(g.split("/")[1])
    if page not in pages:
        pages[page] = render_page(pdf, page, dpi=600).rgb
    img = pages[page]
    m = 110
    x0, y0, x1, y1 = max(int(x) - m, 0), max(int(y) - m, 0), min(int(x + bw) + m, img.shape[1]), min(int(y + bh) + m, img.shape[0])
    c = Image.fromarray(img[y0:y1, x0:x1].copy())
    c.resize((c.width * 2, c.height * 2), Image.LANCZOS).save(out / ("whole-%s-%02d-%s.png" % (tag, k, g.replace("/", "_"))))
    print(k, g, w["status"], w["bar"], "box", [round(v) for v in (x, y, bw, bh)])
