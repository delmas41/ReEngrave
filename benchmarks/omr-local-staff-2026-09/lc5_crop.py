"""lane-lines-combined: ONE crop of a far head with a ruler. Lines drawn 1 px wide (at the crop's scale) in CYAN for the local
staff lines, YELLOW ticks at the left for every ledger rung the reader found, ORANGE for the box it used, MAGENTA for the note's
line it chose. Colours are chosen to show on black ink (Sean: blue disappears)."""
import cv2
import numpy as np

CYAN, YEL, ORG, MAG, GRN = (255, 255, 0), (0, 255, 255), (0, 140, 255), (255, 0, 255), (0, 220, 0)   # BGR


def crop(gray, d, sc=3, pad_x_sp=2.2, pad_y_sp=3.0, show_lines=True):
    """d = one arm's diagnostics: lines, box_used, rungs [{y}], note_first.line_y. Returns a BGR image."""
    lines = d["lines"]
    sp = (max(lines) - min(lines)) / 4.0
    x0, y0, x1, y1 = d["box_used"]
    cx = (x0 + x1) / 2.0
    ax0, ax1 = int(cx - (pad_x_sp + 0.7) * sp), int(cx + (pad_x_sp + 0.7) * sp)
    cy0, cy1 = int(y0 - pad_y_sp * sp), int(y1 + pad_y_sp * sp)
    H, W = gray.shape
    ax0, ax1, cy0, cy1 = max(0, ax0), min(W, ax1), max(0, cy0), min(H, cy1)
    im = cv2.cvtColor(gray[cy0:cy1, ax0:ax1], cv2.COLOR_GRAY2BGR)
    im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)

    def Y(y):
        return int(round((y - cy0 + 0.5) * sc))

    def X(x):
        return int(round((x - ax0 + 0.5) * sc))
    w = im.shape[1]
    if show_lines:
        for y in lines:
            if cy0 <= y < cy1:
                cv2.line(im, (0, Y(y)), (w - 1, Y(y)), CYAN, 1)
    for r in d.get("rungs") or []:
        cv2.line(im, (0, Y(r["y"])), (14, Y(r["y"])), YEL, 1)
        cv2.line(im, (w - 15, Y(r["y"])), (w - 1, Y(r["y"])), YEL, 1)
    ly = (d.get("note_first") or {}).get("line_y")
    if ly is not None:
        cv2.line(im, (w // 2 - 40, Y(ly)), (w // 2 + 40, Y(ly)), MAG, 1)
    cv2.rectangle(im, (X(x0), Y(y0)), (X(x1), Y(y1)), ORG, 1)
    return im
