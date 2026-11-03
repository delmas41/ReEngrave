"""My own look + local measure (not a tile). args: plate page x0,y0,x1,y1(head page box) out.png [more boxes]
Measures the staff lines LOCALLY in a narrow column just left and right of the head (outside it), prints each line's y,
the head's ink vertical extent (rows in the box with ink wider than half the box, excluding line rows), and the
head's position in half-steps from the local top line."""
import sys
import numpy as np
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged import lane_report as L

_CACHE = {}


def page(plate, pg):
    k = (plate, pg)
    if k not in _CACHE:
        _CACHE[k] = np.asarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb)
    return _CACHE[k]


def lines_at(ink, xa, xb, ylo, yhi):
    col = ink[ylo:yhi, xa:xb].mean(axis=1)
    rows = np.nonzero(col > 0.6)[0]
    groups = []
    for r in rows:
        if groups and r - groups[-1][-1] <= 1:
            groups[-1].append(r)
        else:
            groups.append([r])
    return [ylo + (g[0] + g[-1]) / 2.0 for g in groups]


def measure(plate, pg, box):
    a = page(plate, pg)
    g = a.mean(axis=2) if a.ndim == 3 else a
    ink = g < 128
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    w = x1 - x0
    ylo, yhi = y0 - 160, y1 + 160
    left = lines_at(ink, x0 - w, x0 - 2, ylo, yhi)
    right = lines_at(ink, x1 + 2, x1 + w, ylo, yhi)
    return left, right


if __name__ == "__main__":
    plate, pg, box, out = sys.argv[1], int(sys.argv[2]), [float(v) for v in sys.argv[3].split(",")], sys.argv[4]
    left, right = measure(plate, pg, box)
    print("lines left ", [round(v, 1) for v in left])
    print("lines right", [round(v, 1) for v in right])
    a = page(plate, pg)
    im = Image.fromarray(a).convert("RGB")
    d = ImageDraw.Draw(im)
    cols = ["red", "blue", "green", "magenta", "orange"]
    for i, b in enumerate([sys.argv[3]] + sys.argv[5:]):
        bx = [float(v) for v in b.split(",")]
        d.rectangle(bx, outline=cols[i % len(cols)], width=1)
    x0, y0, x1, y1 = box
    reg = (int(x0 - 260), int(y0 - 160), int(x1 + 260), int(y1 + 160))
    c = im.crop(reg)
    c.resize((c.width * 3, c.height * 3), Image.NEAREST).save(out)
