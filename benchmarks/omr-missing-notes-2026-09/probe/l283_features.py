"""l283_features: candidate SHAPE features of the ink at a stem's tip, per Sean's label, on the real erased cell raster.
ROADMAP 2.83 probe: this is where the window and the shape test are chosen, from his flag boxes' measured ink, before
anything is written into gather.py.

    python3 l283_features.py CELLS.pkl.gz
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from l283_common import cell_space, to_page  # noqa: E402
from l283_dataset import build  # noqa: E402


def head_edges_canonical(T, cell):
    """Sean's head boxes inside this cell, in canonical px: (x0, y0, x1, y1)."""
    bx0, by0, bx1, by1 = cell["bbox_page_px"]
    s = cell["scale"]
    out = []
    for h in T.heads:
        r = h.rect
        cx_, cy_ = (r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0
        if bx0 <= cx_ < bx1 and by0 <= cy_ < by1:
            out.append(((r[0] - bx0) * s, (r[1] - by0) * s, (r[2] - bx0) * s, (r[3] - by0) * s))
    return out


def features(img, x0, x1, tip_y, sign, space, heads):
    """img: bool ink mask in the cell's canonical frame. Everything in the cell's pixels; `t` = spaces from the tip
    into the stem's body (+), `u` = spaces to the right of the stem's right edge (+)."""
    import cv2
    H, W = img.shape
    # the stem body is cut at the first head that stands beside it (the head's own ink is not a flag)
    t_head = 4.0
    for hx0, hy0, hx1, hy1 in heads:
        if hx1 < x0 - 0.2 * space or hx0 > x1 + 1.8 * space:
            continue
        near = (hy0 - tip_y) * sign if sign > 0 else (tip_y - hy1)
        far = (hy1 - tip_y) * sign if sign > 0 else (tip_y - hy0)
        near, far = near / space, far / space
        if far > 0.0 and near > 0.3:
            t_head = min(t_head, near - 0.1)
        elif far > 0.0 and near <= 0.3:
            t_head = 0.0      # the head stands AT this end
    out = {"t_head": round(t_head, 2)}
    if t_head < 1.0:
        out["status"] = "no_room"
        return out
    ya, yb = sorted((tip_y - sign * 0.5 * space, tip_y + sign * t_head * space))
    xa, xb = int(round(x0 - 1.0 * space)), int(round(x1 + 2.0 * space))
    ya, yb, xa, xb = max(0, int(round(ya))), min(H, int(round(yb))), max(0, xa), min(W, xb)
    if yb - ya < 4 or xb - xa < 4:
        out["status"] = "off"
        return out
    sub = img[ya:yb, xa:xb].astype(np.uint8)
    k = max(1, int(round(0.06 * space)))
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    n, lab = cv2.connectedComponents(sub, connectivity=8)
    sx0, sx1 = int(round(x0)) - xa, int(round(x1)) - xa + 1
    # seed: the stem's own columns, in the first 1.0 space from the tip (the root)
    if sign > 0:
        r0, r1 = int(round(tip_y)) - ya, int(round(tip_y + 1.0 * space)) - ya
    else:
        r0, r1 = int(round(tip_y - 1.0 * space)) - ya, int(round(tip_y)) - ya
    r0, r1 = max(0, r0), min(sub.shape[0], r1)
    seeds = set(np.unique(lab[r0:r1, max(0, sx0):sx1]).tolist()) - {0}
    comp = np.isin(lab, list(seeds)) if seeds else np.zeros_like(lab, bool)
    # t and u for every pixel
    ys = np.arange(ya, yb)
    t = (ys - tip_y) * sign / space
    xs = np.arange(xa, xb)
    u = (xs - x1) / space
    ul = (x0 - xs) / space
    right = comp & (u[None, :] > 0.04)
    left = comp & (ul[None, :] > 0.04)
    out["status"] = "ok"
    out["seeded"] = bool(seeds)
    out["right_px"] = int(right.sum())
    out["left_px"] = int(left.sum())

    def band(m, t0, t1, u0, u1, uu=u):
        rows = (t >= t0) & (t < t1)
        cols = (uu >= u0) & (uu < u1)
        if not rows.any() or not cols.any():
            return 0.0
        return float(m[np.ix_(rows, cols)].mean())
    out["root"] = round(band(right, -0.2, 0.9, 0.05, 0.75), 3)
    out["arm"] = round(band(right, 0.9, 2.6, 0.4, 1.2), 3)
    out["near_left"] = round(band(left, -0.2, 2.0, 0.05, 0.9, ul), 3)
    # extents of the attached right ink
    if right.any():
        rr, cc = np.where(right)
        out["x_out"] = round(float(u[cc].max()), 2)
        out["t_first"] = round(float(t[rr].min()), 2)
        out["t_last"] = round(float(t[rr].max()), 2)
        # rows (0.05 sp) holding attached right ink beyond 0.4 sp from the stem: the arm's length along the stem
        far = right[:, u > 0.4]
        out["arm_rows"] = round(float(far.any(axis=1).sum()) / (0.05 * space), 2) if far.size else 0.0
    else:
        out.update(x_out=0.0, t_first=None, t_last=None, arm_rows=0.0)
    return out


def main():
    T, cells, rows = build(sys.argv[1])
    res = collections.defaultdict(list)
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        f = features(c["img"], x, x + w, tip_y, sign, s, head_edges_canonical(T, c))
        f["stem"] = r["stem"]
        res[r["label"]].append(f)
    keys = ("root", "arm", "near_left", "x_out", "t_first", "t_last", "arm_rows")
    for lab in ("flag", "bare", "beam"):
        L = [f for f in res[lab]]
        print(f"\n== {lab} n={len(L)}  status {collections.Counter(f['status'] for f in L)}")
        for f in sorted((f for f in L if f["status"] == "ok"), key=lambda f: -f["root"]):
            print("  ", f["stem"], " ".join(f"{k}={f.get(k)}" for k in keys), "t_head", f["t_head"])


if __name__ == "__main__":
    main()
