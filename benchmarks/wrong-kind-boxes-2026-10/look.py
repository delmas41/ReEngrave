"""ROADMAP 2.245 -- contact sheets of detector boxes for the LANE's own look (rule 7: check a count with crops before trusting it).

Not Sean's tiles (those are `tiles.py`): each crop here is one box on its own staff with the box drawn, a caption with the box's class,
size in staff spaces and confidence. Input: a JSON list of {plate, page, pb: [x0, y0, x1, y1], caption}. Output: one PNG sheet.
Usage: python3 benchmarks/wrong-kind-boxes-2026-10/look.py PICKS.json OUT.png
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import cell_map as CM  # noqa: E402
from tools.omr.staged import claim_readout as CR  # noqa: E402

SL = CR.RECORDS / "lane-report-slices-20261029-night"
_PDF = {}


def pdf_of(plate):
    if plate not in _PDF:
        rows = CR.read_rows(SL / plate, [CR.slice_pages(SL / plate)[0]])
        _PDF[plate] = CR.LIB / CR.edition_info(rows)["edition_path"]
    return _PDF[plate]


_PAGES = {}


def page(plate, p):
    k = (plate, p)
    if k not in _PAGES:
        if len(_PAGES) > 3:
            _PAGES.clear()
        (pws, cells), = CM.load_prepared(pdf_of(plate), [p])
        sp = float(np.median([s.line_spacing_px for s in pws.staves]))
        _PAGES[k] = (pws, Image.fromarray(pws.page.rgb).convert("RGB"), sp)
    return _PAGES[k]


def nearest_staff(pws, y):
    return min(pws.staves, key=lambda s: 0 if s.top_y <= y <= s.bottom_y else min(abs(y - s.top_y), abs(y - s.bottom_y)))


def crop(plate, p, box, draw=True, size=(260, 200)):
    pws, img, sp = page(plate, p)
    x0, y0, x1, y1 = box
    st = nearest_staff(pws, (y0 + y1) / 2)
    cx = (x0 + x1) / 2
    ta = int(min(st.top_y - 1.5 * sp, y0 - 1.5 * sp))
    tb = int(max(st.bottom_y + 1.5 * sp, y1 + 1.5 * sp))
    tl = int(min(cx - 5 * sp, x0 - sp))
    tr = int(max(cx + 5 * sp, x1 + sp))
    t = img.crop((tl, ta, tr, tb)).copy()
    if draw:
        ImageDraw.Draw(t).rectangle([x0 - tl - 3, y0 - ta - 3, x1 - tl + 3, y1 - ta + 3], outline=(255, 120, 0), width=2)
    return t, (tl, ta), st


def sheet(picks, out, cols=6, cw=260, ch=200):
    rows = (len(picks) + cols - 1) // cols
    S = Image.new("RGB", (cols * cw, rows * (ch + 14)), "white")
    d = ImageDraw.Draw(S)
    for i, pk in enumerate(picks):
        t, _, _ = crop(pk["plate"], pk["page"], pk["pb"])
        t.thumbnail((cw - 4, ch - 4))
        x, y = (i % cols) * cw, (i // cols) * (ch + 14)
        S.paste(t, (x + 2, y + 2))
        d.text((x + 2, y + ch), "%d %s" % (i + 1, pk.get("caption", ""))[:44], fill=(0, 0, 0))
    S.save(out)


if __name__ == "__main__":
    sheet(json.loads(pathlib.Path(sys.argv[1]).read_text()), sys.argv[2])
