"""ROADMAP 2.179 -- contact sheets of a census (c1_census.py) for MY look at every red bar (ours, not evidence; never sent to Sean).

usage: python3 benchmarks/omr-unseen-symbols-2026-10/probe/s1_sheets.py DOC PDF RECORD CENSUS.json OUTDIR [PER_SHEET]
Each bar: the plain print (top) and the same print with boxes (below), staff +-3.5 spaces, 36 px a staff space.
green = a record note/rest/flag/dot box no gate refused; red = refused by a gate; orange = a box under the 0.25 floor
not in the record (class, score x100); blue label = a box the small view (2.172) added. Header: index, bar, want/counted, rows.
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

doc, pdf, rec_path, census_path, outdir = sys.argv[1:6]
per = int(sys.argv[6]) if len(sys.argv) > 6 else 6
os.makedirs(outdir, exist_ok=True)
census = json.load(open(census_path))
rec = load_record(rec_path)["record"]
lines = {}
for o in rec["observations"]:
    if o["quantity"] == "staff_lines" and o["subject"].startswith("staff/"):
        lines.setdefault(o["subject"][6:], o["value"])
SP = 36.0


def abbrev(c):
    for a, b in (("noteheadBlack", "hB"), ("noteheadHalf", "hH"), ("noteheadWhole", "hW"), ("notehead", "h"), ("InSpace", ""),
                 ("OnLine", ""), ("augmentationDot", "dot"), ("rest", "r"), ("flag", "f"), ("Quarter", "4"), ("Half", "2"),
                 ("Whole", "1"), ("8th", "8"), ("16th", "16"), ("32nd", "32"), ("Up", "^"), ("Down", "v")):
        c = c.replace(a, b)
    return c[:6]


def tile(page, e, idx):
    p, s, st, _c = e["bar"].split("/")
    ys = lines.get("%s/%s/%s" % (p, s, st))
    x0, y0, x1, y1 = e["cell_box"]
    if ys:
        sp = (ys[-1] - ys[0]) / 4.0
        Y0, Y1 = ys[0] - 3.5 * sp, ys[-1] + 3.5 * sp
    else:
        sp = (y1 - y0) / 14.0
        Y0, Y1 = y0, y1
    X0, X1 = x0 - 0.7 * sp, x1 + 0.7 * sp
    X0, Y0 = int(max(0, X0)), int(max(0, Y0))
    X1, Y1 = int(min(page.shape[1], X1)), int(min(page.shape[0], Y1))
    k = SP / sp
    crop = cv2.resize(page[Y0:Y1, X0:X1], None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
    ann = crop.copy()

    def rect(b, col, lab, lcol=None):
        a = (int((b[0] - X0) * k), int((b[1] - Y0) * k))
        z = (int((b[2] - X0) * k), int((b[3] - Y0) * k))
        cv2.rectangle(ann, a, z, col, 2)
        cv2.putText(ann, lab, (a[0], max(10, a[1] - 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.42, lcol or col, 1)
    for gs, g in e["record"].items():
        col = (0, 0, 230) if g["refused"] else (0, 150, 0)
        rect(g["box"], col, gs.split("/")[-1] + abbrev(g["cls"]), (230, 80, 0) if g.get("reader") == "yolo_detector_view" else None)
    for sb in e["subfloor"]:
        rect(sb["box"], (0, 140, 255), "%s%02d" % (abbrev(sb["cls"]), int(sb["conf"] * 100)))
    w = max(crop.shape[1], 360)
    pad = lambda im: np.hstack([im, np.full((im.shape[0], w - im.shape[1], 3), 255, np.uint8)]) if im.shape[1] < w else im
    hdr = np.full((44, w, 3), 255, np.uint8)
    cv2.putText(hdr, "%d %s want %s got %s" % (idx, e["bar"], e["want"], e["counted"]), (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    rows = " ".join(("" if k_ == "note" else "R") + str(t)[:3].replace("rest", "") + ("*" if stt != "READ" else "")
                    for k_, t, _b, stt, _g, _p in e["rows"])
    cv2.putText(hdr, rows[:int(w / 7.5)], (3, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    return np.vstack([hdr, pad(crop), np.full((4, w, 3), 160, np.uint8), pad(ann)])


pages = {}
for p in sorted({int(e["bar"].split("/")[0]) for e in census}):
    pages[p] = cv2.cvtColor(render_page(pdf, p).rgb, cv2.COLOR_RGB2BGR)
tiles = [tile(pages[int(e["bar"].split("/")[0])], e, i) for i, e in enumerate(census) if e.get("cell_box")]
MAXW = 1900
sheet, row, rows_, n = [], [], [], 0


def flush_row():
    global row
    if row:
        h = max(t.shape[0] for t in row)
        rows_.append(np.hstack([np.vstack([t, np.full((h - t.shape[0], t.shape[1], 3), 255, np.uint8)]) for t in row]))
        row = []


def flush_sheet(name):
    global rows_
    flush_row()
    if rows_:
        W = max(r.shape[1] for r in rows_)
        im = np.vstack([np.hstack([r, np.full((r.shape[0], W - r.shape[1], 3), 255, np.uint8)]) for r in rows_])
        cv2.imwrite(os.path.join(outdir, name), im)
        rows_ = []


sid = 0
cnt = 0
for t in tiles:
    t = np.hstack([t, np.full((t.shape[0], 10, 3), 255, np.uint8)])
    if sum(x.shape[1] for x in row) + t.shape[1] > MAXW:
        flush_row()
    row.append(t)
    cnt += 1
    if cnt % per == 0:
        flush_sheet("%s_sheet%02d.png" % (doc, sid))
        sid += 1
flush_sheet("%s_sheet%02d.png" % (doc, sid))
print("sheets", sid + 1)
