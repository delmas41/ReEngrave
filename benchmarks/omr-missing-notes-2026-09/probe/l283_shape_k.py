"""l283_shape_k (a copy of l283_shape with the closing kernel a parameter, for the 2.83 closing experiment): the candidate flag-SHAPE reading at a stem's tip, scored on Sean's page-0 stems by his label, on the real
erased cell raster. ROADMAP 2.83 probe: the numbers below are tuned HERE and are labelled as chosen on this page; the
blind tiles, the other pages and the guard counts are what test them.

    python3 l283_shape.py CELLS.pkl.gz [--list]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402
from l283_features import head_edges_canonical  # noqa: E402

# ---- candidate parameters (staff spaces, local) ----
NEAR = -0.3          # the window starts this far PAST the tip (a rounded tip, a flag root drawn over the end)
FAR = 3.6            # and runs this far back along the stem, cut at the stem's own head
OUT_MIN = 0.45       # a flag stands out at least this far from the stem's right edge
OUT_MAX = 1.5        # ... and no farther (a beam / slur that runs on is not a flag)
ARM_MIN = 0.45       # ink at least this far out (u > ARM_U) on at least this length of the stem (flags 0.55 .. 2.5; non-flags <= 0.37)
ARM_U = 0.35
ROOT_T_MAX = 1.2     # a flag's ink starts within this far of the tip (measured on his 21 read flags: 0.42 .. 0.81)
EDGE_U = 0.15       # ink nearer the stem than this is the stem's own edge, not a mark
LEFT_AREA_MAX = 0.05  # attached ink on the LEFT, space^2 (a flag hangs from one side)
EMPTY_AREA = 0.02    # right-attached ink under this many space^2 is "nothing hangs from this tip"
NEAR_U = 0.30        # a crossing line's stub is read at the stem's side (0.04..0.30) ...
FAR_U = 0.90         # ... and further out (0.30..0.90), on each side
LINE_FILL = 0.6
LINE_MAX_THICK = 0.45  # spaces: a crossing stub thicker than this is a bar, not a line


def read(ink, x0, x1, tip_y, sign, space, head_t=None, kclose=0.06, frag=None):
    import cv2
    H, W = ink.shape
    far = FAR if head_t is None else min(FAR, head_t)
    if far < 1.2:
        return {"v": "decline", "why": "no_room"}
    ya, yb = sorted((tip_y + sign * NEAR * space, tip_y + sign * far * space))
    xa, xb = int(round(x0 - 1.0 * space)), int(round(x1 + 2.6 * space))
    ya, yb, xa, xb = max(0, int(round(ya))), min(H, int(round(yb))), max(0, xa), min(W, xb)
    if yb - ya < 4 or xb - xa < 4:
        return {"v": "decline", "why": "off"}
    sub = ink[ya:yb, xa:xb].astype(np.uint8)
    k = max(1, int(round(kclose * space)))
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    _n, lab = cv2.connectedComponents(sub, connectivity=8)
    sx0, sx1 = max(0, int(round(x0)) - xa), min(sub.shape[1], int(round(x1)) - xa + 1)
    ts = (np.arange(ya, yb) - tip_y) * sign / space
    us = (np.arange(xa, xb) - x1) / space
    ul = (x0 - np.arange(xa, xb)) / space
    seed_rows = (ts >= NEAR) & (ts <= 1.0)
    seeds = set(np.unique(lab[np.ix_(seed_rows, np.arange(sx0, sx1))]).tolist()) - {0}
    if not seeds:
        return {"v": "decline", "why": "no_stem_ink"}
    comp = np.isin(lab, list(seeds))
    if frag:
        # FRAGMENTS: components a hairline break leaves beside the attached ink (parameters: gap, t_max, area, width in spaces)
        gap_sp, t_max, area_min, width_min = frag
        import cv2 as _cv
        dist = _cv.distanceTransform((~comp).astype(np.uint8), _cv.DIST_L2, 3)
        n2, lab2, st2, _c = _cv.connectedComponentsWithStats(sub, connectivity=8)
        # (labels of `lab` were computed on the closed image: re-label the closed image's non-seed components here)
        nn = int(lab.max())
        for i in range(1, nn + 1):
            if i in seeds:
                continue
            m = lab == i
            ys_, xs_ = np.where(m)
            if ys_.size == 0:
                continue
            a_sp = ys_.size / (space * space)
            u_lo = us[xs_.min()]
            w_sp = (xs_.max() - xs_.min() + 1) / space
            t_lo = ts[ys_].min()
            if a_sp >= area_min and w_sp >= width_min and u_lo >= 0.05 and t_lo <= t_max \
                    and float(dist[m].min()) / space <= gap_sp:
                comp = comp | m
    right = comp & (us[None, :] > 0.04)
    left = comp & (ul[None, :] > 0.04)

    def fill(m, u, lo, hi):
        cols = (u >= lo) & (u <= hi)
        return m[:, cols].mean(axis=1) if cols.any() else np.zeros(m.shape[0])
    # ROWS A LINE CROSSES: attached ink on BOTH sides of the stem in the same row, standing out >= FAR_U on at least one
    # side -- a ledger / staff-line stub or a slur's belly, never a flag (a flag hangs from ONE side). A THIN run of
    # such rows is a line's stub and is left out of every measure; a THICK run is a bar and the tip is not readable.
    both = (fill(right, us, 0.04, NEAR_U) >= LINE_FILL) & (fill(left, ul, 0.04, NEAR_U) >= LINE_FILL)
    far_side = (fill(right, us, NEAR_U, FAR_U) >= LINE_FILL) | (fill(left, ul, NEAR_U, FAR_U) >= LINE_FILL)
    on_line = both & far_side
    run = 0
    for v in list(on_line) + [False]:
        if v:
            run += 1
        else:
            if run > LINE_MAX_THICK * space:
                return {"v": "decline", "why": "crosses_both_sides", "bar_sp": round(run / space, 2)}
            run = 0
    on_line = on_line | np.roll(on_line, 1) | np.roll(on_line, -1)
    keep = ~on_line
    d = {"line_rows_sp": round(float(on_line.sum()) / space, 2)}
    if keep.sum() < 0.5 * len(keep):
        return dict(d, v="decline", why="lines_take_the_window")
    right, left = right[keep], left[keep]
    left_area = float(left[:, ul >= EDGE_U].sum()) / (space * space)
    right_far = right[:, us >= EDGE_U]
    area = float(right_far.sum()) / (space * space)
    d.update(area=round(area, 3), left=round(left_area, 3))
    if left_area > LEFT_AREA_MAX:
        return dict(d, v="decline", why="crosses_both_sides")
    if area < EMPTY_AREA:
        return dict(d, v="none", why="empty")
    out = float(us[(us >= EDGE_U)][np.where(right_far.any(axis=0))[0]].max())
    d["out"] = round(out, 2)
    if out > OUT_MAX:
        return dict(d, v="decline", why="runs_on")
    arm = float(right[:, us > ARM_U].any(axis=1).sum()) / space
    ts_kept = ts[keep]
    t_first = float(ts_kept[right_far.any(axis=1)].min())
    d["arm"] = round(arm, 2)
    d["t_first"] = round(t_first, 2)
    # A flag HANGS FROM THE TIP: its ink starts within `ROOT_T_MAX` of it. Ink that starts further in (a ledger line's
    # stub cut by the window's far edge, a neighbour's mark touching the stem mid-way) is something else.
    if out >= OUT_MIN and arm >= ARM_MIN and t_first <= ROOT_T_MAX:
        return dict(d, v="flag", why="shaped")
    return dict(d, v="decline", why="ink_not_flag_shaped")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    T, cells, rows = build(a.cells)
    res = []
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        heads = head_edges_canonical(T, c)
        # head cut, the same arithmetic as gather._head_edge_for_end
        head_t, here = None, False
        for hx0, hy0, hx1, hy1 in heads:
            if hx0 >= x + w + 1.8 * s or hx1 <= x - 1.8 * s:
                continue
            near, far = (hy0, hy1) if sign > 0 else (hy1, hy0)
            t_near, t_far = (near - tip_y) * sign / s, (far - tip_y) * sign / s
            if t_near <= 0.3 and t_far > -0.3:
                here = True
            elif t_near > 0.3 and (head_t is None or t_near < head_t):
                head_t = t_near - 0.1
        if here:
            res.append((r, {"v": "decline", "why": "head_at_this_end"}))
            continue
        res.append((r, read(c["img"], x, x + w, tip_y, sign, s, head_t)))
    tab = collections.defaultdict(collections.Counter)
    for r, m in res:
        tab[r["label"]][m["v"] + ":" + m["why"]] += 1
    for lab in ("flag", "bare", "beam"):
        print(lab, dict(tab[lab]))
    if a.list:
        for lab in ("flag", "bare", "beam"):
            print("--", lab)
            for r, m in res:
                if r["label"] == lab and not (lab != "flag" and m["v"] == "none"):
                    print("  ", r["stem"], m)


if __name__ == "__main__":
    main()
