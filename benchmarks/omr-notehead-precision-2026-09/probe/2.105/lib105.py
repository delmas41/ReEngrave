"""ROADMAP 2.105 shared helpers: page boxes + staff spacing off a record, a
600-dpi crop with corner brackets, and a contact sheet. Probe-only."""
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "benchmarks" / "omr-missing-notes-2026-09" / "probe"))

from l281_tiles import PDFS  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

TILE_SP = 32.0
HALF_W_SP = 6.0
_pages = {}


def page_rgb(mv, page):
    k = (mv, page)
    if k not in _pages:
        _pages[k] = render_page(PDFS[mv], page, dpi=600).rgb
    return _pages[k]


def staff_spacing(run):
    sp = {}
    for o in run.observations:
        if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
            ys = o["value"]
            sp[o["subject"]] = (ys[-1] - ys[0]) / (len(ys) - 1)
    return sp


def crop(img, boxes, sp, half_h_sp=5.5, label=None):
    """boxes: [(x0,y0,x1,y1,(r,g,b))]; the window is centred on the first."""
    x0, y0, x1, y1, _ = boxes[0]
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    X0, X1 = int(cx - HALF_W_SP * sp), int(cx + HALF_W_SP * sp)
    Y0, Y1 = int(cy - half_h_sp * sp), int(cy + half_h_sp * sp)
    H, W = img.shape[:2]
    c = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
    xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    if xb > xa and yb > ya:
        c[ya - Y0:yb - Y0, xa - X0:xb - X0] = img[ya:yb, xa:xb]
    f = TILE_SP / sp
    c = cv2.resize(c, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC if f > 1 else cv2.INTER_AREA)
    for (bx0, by0, bx1, by1, col) in boxes:
        pad, arm, t = 3, 11, 3
        a, b = int((bx0 - X0) * f - pad), int((by0 - Y0) * f - pad)
        cc, d = int((bx1 - X0) * f + pad), int((by1 - Y0) * f + pad)
        for (x, y, dx, dy) in ((a, b, 1, 1), (cc, b, -1, 1), (a, d, 1, -1), (cc, d, -1, -1)):
            cv2.line(c, (x, y), (x + dx * arm, y), col, t)
            cv2.line(c, (x, y), (x, y + dy * arm), col, t)
    if label:
        cv2.putText(c, label, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 0), 1, cv2.LINE_AA)
    return c


def sheet(tiles, cols=4):
    h = max(t.shape[0] for t in tiles)
    w = max(t.shape[1] for t in tiles)
    rows = []
    for i in range(0, len(tiles), cols):
        row = tiles[i:i + cols]
        row = [np.pad(t, ((0, h - t.shape[0]), (0, w - t.shape[1]), (0, 0)), constant_values=255) for t in row]
        while len(row) < cols:
            row.append(np.full((h, w, 3), 255, np.uint8))
        rows.append(np.hstack(row))
    return np.vstack(rows)
