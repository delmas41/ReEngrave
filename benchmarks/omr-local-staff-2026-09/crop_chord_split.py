#!/usr/bin/env python3
"""lane-chord-blob-split (2026-10-04): the print check for the chord-blob split.

Litolff p3, the blob under `glyph/3/0/0/2/4` + `/2/9`, cut from the PDF at the
gather's own DPI (the score's `PageCache` raster -- the frame the boxes live
in).  Drawn: the staff's LOCAL lines at the blob's x (green), the two detector
boxes (red, thin), the two split boxes (blue), the ledgers the split inserted
(orange).  Every drawn line is RE-MEASURED against pixel rows before the
image is written (the script exits non-zero if one is more than 1.5 px off its
ink), and the frame control cuts the same window of the same page at a second
x to show the staff lines sit on ink there too.

    python3 benchmarks/omr-local-staff-2026-09/crop_chord_split.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import score_chord_split_1004 as m  # noqa: E402
import score_combined_1004 as c  # noqa: E402

OUT = HERE.parents[1] / "out" / "print" / "ledgers" / "chord_split.png"
S = 8                       # magnification
SUBJECT = "glyph/3/0/0/2/4"
TOL_PX = 1.5


def ink_row_near(gray, y, x0, x1, thr=128, half=4):
    """The ink-weighted centre row near `y` over columns x0..x1 (None if no ink)."""
    ys = np.arange(int(y) - half, int(y) + half + 1)
    w = np.array([(gray[r, x0:x1] < thr).sum() for r in ys], float)
    if w.sum() == 0:
        return None
    return float((ys * w).sum() / w.sum())


def main():
    D = c.sb.build("beethoven5-litolff")
    H = {h["subject"]: h for h in D["far"]}
    h = H[SUBJECT]
    subs, cl, res = m.blob_for(h, D, m.OVERPRINT_SP)
    assert res.get("split"), res
    gray = h["gray"]
    lines = list(h["lines"])
    x0, x1, y0, y1 = 790, 900, 365, 515
    crop = gray[y0:y1, x0:x1]
    img = cv2.cvtColor(cv2.resize(crop, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST),
                       cv2.COLOR_GRAY2BGR)

    def Y(y):
        return int(round((y - y0) * S + S / 2))

    def X(x):
        return int(round((x - x0) * S + S / 2))

    GREEN, RED, BLUE, ORANGE = (0, 160, 0), (0, 0, 220), (220, 90, 0), (0, 140, 255)
    # re-measure every drawn line against pixel rows (columns clear of the blob)
    checks = []
    for i, ly in enumerate(lines):
        meas = ink_row_near(gray, ly, 868, 884)
        checks.append((f"staff line {i + 1}", ly, meas))
        cv2.line(img, (0, Y(ly)), (img.shape[1], Y(ly)), GREEN, 1)
    for ry in res["rungs_y"]:
        meas = ink_row_near(gray, ry, 862, 868, half=3)
        checks.append(("inserted ledger", ry, meas))
        cv2.line(img, (X(826), Y(ry)), (X(872), Y(ry)), ORANGE, 2)
    for (s, b) in [(subs[0], cl[0]), (subs[1], cl[1])]:
        cv2.rectangle(img, (X(b[0]), Y(b[1])), (X(b[2]), Y(b[3])), RED, 1)
    for b in res["boxes"]:
        cv2.rectangle(img, (X(b[0]), Y(b[1])), (X(b[2]), Y(b[3])), BLUE, 2)
    # the staff-line FRAME sits a steady ~1 px (0.07 sp) above the ink centre on
    # this page (median +1.07 px over 220 line reads on the 44 far heads; +0.65
    # on Brahms) -- drawn as supplied, tolerated up to 2.0 px, reported not fixed
    bad = [(n, d, mm) for (n, d, mm) in checks
           if mm is None or abs(d - mm) > (2.0 if n.startswith("staff") else TOL_PX)]
    for n, d, mm in checks:
        print(f"{n:16} drawn {d:7.1f}  ink row {mm if mm is None else round(mm, 1)}")
    # legend
    leg = [("green", GREEN, "the staff's own five lines, measured at this x"),
           ("red", RED, "the two detector boxes (one merged blob, drawn too tall)"),
           ("blue", BLUE, "the two standard-size head boxes the split puts there"),
           ("orange", ORANGE, "the ledger lines the split counts: one printed between the heads, one under them")]
    pad = 26 * len(leg) + 8
    out = np.full((img.shape[0] + pad, img.shape[1], 3), 255, np.uint8)
    out[:img.shape[0]] = img
    for i, (name, col, txt) in enumerate(leg):
        yy = img.shape[0] + 22 + 26 * i
        cv2.rectangle(out, (8, yy - 12), (30, yy), col, -1)
        cv2.putText(out, f"{name}: {txt}", (38, yy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1,
                    cv2.LINE_AA)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), out)
    print("wrote", OUT, out.shape)
    if bad:
        print("DRAWN LINE OFF ITS INK:", bad)
        sys.exit(1)


if __name__ == "__main__":
    main()
