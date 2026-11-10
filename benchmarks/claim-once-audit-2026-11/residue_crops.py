"""2.283: crops of the biggest 'residue:horizontal' pieces and the biggest 'unclaimed:blob' pieces on one page (claim_readout's own canvas; READ-ONLY).
usage: residue_crops.py PLATE PAGE OUTDIR"""
import os
import pathlib
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
import cv2                                                    # noqa: E402
import numpy as np                                            # noqa: E402
from PIL import Image, ImageDraw                              # noqa: E402
from tools.omr.staged import claim_readout as CR              # noqa: E402
from tools.omr.staged import cell_map as CM                   # noqa: E402

plate, page, out = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
SL = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night") / plate
rows = CR.read_rows(SL, [page])
ed = CR.edition_info(rows)
pdf = CR.LIB / ed["edition_path"]
canvas, verify, pws, cells = CR.build_page(rows, pdf, page, CM.ROOT_DEFAULT)
img = Image.fromarray(pws.page.rgb).convert("RGB")
for name in ("residue:horizontal", "unclaimed:blob"):
    if name not in canvas.cat_names:
        continue
    m = ((canvas.cat == canvas.cat_names.index(name)) & canvas.ink).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((3, 3), np.uint8)), connectivity=8)
    comps = sorted(((int(stats[i][4]), stats[i][:4]) for i in range(1, n)), key=lambda t: -t[0])
    comps = [c for c in comps if c[1][2] < 400 and c[1][3] < 400][:2]
    print(name, "total px", int(m.sum()), "n components", n - 1, "top", [(c[0], list(map(int, c[1]))) for c in comps])
    for k, (px, (x, y, w, h)) in enumerate(comps):
        pad = 70
        x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(img.width, x + w + pad), min(img.height, y + h + pad)
        t = img.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(t).rectangle([x - x0, y - y0, x + w - x0, y + h - y0], outline=(255, 140, 0), width=2)
        t.save(out / ("%s_p%d_%s_%d.png" % (plate, page, name.replace(":", "-"), k)))
