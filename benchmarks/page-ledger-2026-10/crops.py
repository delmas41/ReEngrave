"""ROADMAP 2.240: six blind tiles for Sean -- "is this one mark?" -- at places where the cell cut sees ink twice or cuts it.

One staff per tile (the staff nearest the mark, +-5 sp), a thin box at the mark's own extent, nothing else drawn. key.json is written
OUTSIDE the tile folder. Sources: the straddles found by measure_cells.py (ink continuous across a barline column, cut into two
cells) and detector boxes from the record slice (one mark boxed from two staves' cells; a neighbour staff's line boxed in a pad).
Usage: python3 benchmarks/page-ledger-2026-10/crops.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import cell_map as CM  # noqa: E402
from tools.omr.staged import claim_readout as CR  # noqa: E402

OUT = ROOT / "out/print/2.240-crops"
SL = CR.RECORDS / "lane-report-slices-20261029-night"


def pdf_of(plate):
    rows = CR.read_rows(SL / plate, [CR.slice_pages(SL / plate)[0]])
    return CR.LIB / CR.edition_info(rows)["edition_path"]


def _run_len(m, axis):
    """Per True pixel, the length of the run of True it sits in along `axis`."""
    m2 = m if axis == 0 else m.T
    out = np.zeros(m2.shape, np.int32)
    for j in range(m2.shape[1]):
        col = m2[:, j]
        if not col.any():
            continue
        d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
        s, e = np.where(d == 1)[0], np.where(d == -1)[0]
        for a, b in zip(s, e):
            out[a:b, j] = b - a
    return out if axis == 0 else out.T


def component_box(er, x, y, sp, cut_x=None):
    """The erased-ink connected piece through (x, y), within +-8 sp; staff lines already removed."""
    H, W = er.shape
    a, b = max(0, int(y - 4 * sp)), min(H, int(y + 4 * sp))
    c, d = max(0, int(x - 8 * sp)), min(W, int(x + 8 * sp))
    sub = er[a:b, c:d].copy()
    # keep the thin crossing stroke only: drop vertical runs taller than 0.8 sp (stems, the barline) and horizontal runs longer
    # than 12 sp (staff-line remnants)
    vr = _run_len(sub, axis=0)
    hr = _run_len(sub, axis=1)
    sub &= (vr <= 0.8 * sp) & (hr <= 12 * sp)
    lab, _ = ndimage.label(sub, structure=np.ones((3, 3)))
    yy, xx = int(y - a), int(x - c)
    k = int(0.8 * sp)
    win = lab[max(0, yy - 2):yy + 3, max(0, xx - k):xx + k + 1]
    ids = [v for v in np.unique(win) if v]
    if not ids:
        return None
    m = np.isin(lab, ids)
    ys, xs = np.where(m)
    return [int(xs.min() + c), int(ys.min() + a), int(xs.max() + c), int(ys.max() + a)]


def tile(img, staff, box, sp, path):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    ta = int(min(staff.top_y - 2 * sp, y0 - 1.5 * sp))
    tb = int(max(staff.bottom_y + 2 * sp, y1 + 1.5 * sp))
    tl = int(min(cx - 6 * sp, x0 - sp))
    tr = int(max(cx + 6 * sp, x1 + sp))
    t = img.crop((tl, ta, tr, tb)).copy()
    dr = ImageDraw.Draw(t)
    dr.rectangle([x0 - tl - 3, y0 - ta - 3, x1 - tl + 3, y1 - ta + 3], outline=(255, 120, 0), width=2)
    t.save(path)


def nearest_staff(pws, y):
    return min(pws.staves, key=lambda s: 0 if s.top_y <= y <= s.bottom_y else min(abs(y - s.top_y), abs(y - s.bottom_y)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tiles").mkdir(exist_ok=True)
    picks = json.loads((pathlib.Path(__file__).parent / "crop_picks.json").read_text())
    key = []
    loaded = {}
    for i, pk in enumerate(picks, 1):
        lk = (pk["plate"], pk["page"])
        if lk not in loaded:
            loaded.clear()
            (pws, cells), = CM.load_prepared(pdf_of(pk["plate"]), [pk["page"]])
            er = AS.composite_ink(pws.page.binary, cells)
            loaded[lk] = (pws, cells, er, Image.fromarray(pws.page.rgb).convert("RGB"))
        pws, cells, er, img = loaded[lk]
        sp = float(np.median([s.line_spacing_px for s in pws.staves]))
        box = pk.get("box") or component_box(er, pk["x"], pk["y"], sp)
        if box is None:
            print("no ink at", pk)
            continue
        st = nearest_staff(pws, (box[1] + box[3]) / 2)
        name = "tile%02d.png" % i
        tile(img, st, box, sp, OUT / "tiles" / name)
        key.append({"tile": name, **pk, "box_page_px": box, "staff_index": int(st.staff_index),
                    "question": "is this one mark?"})
    (OUT / "key.json").write_text(json.dumps(key, indent=1))
    print("wrote", len(key), "tiles")


if __name__ == "__main__":
    main()
