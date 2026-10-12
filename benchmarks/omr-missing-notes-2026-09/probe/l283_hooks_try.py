"""l283_hooks_try: the 2.69 hook counter (`gather.stem_tip_hooks`) with the thin-line rows left out, scored on the
flagged stems of Sean's page, ungated and gated by the new shape reading. A probe: where it works, the same change is made
in `gather.stem_tip_hooks`. ROADMAP 2.83 probe.

    python3 l283_hooks_try.py CELLS.pkl.gz
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402
from l283_features import head_edges_canonical  # noqa: E402
import l283_shape as SH  # noqa: E402


def hooks_masked(img, x0, x1, tip_y, sign, space, head_edge=None):
    """`gather.stem_tip_hooks` with the rows a thin line crosses on BOTH sides left out of the left guard and of the runs."""
    import cv2
    from tools.omr.staged import gather as G
    H, W = img.shape
    ya = tip_y - sign * 0.2 * space
    yb = tip_y + sign * G.STEM_TIP_HOOKS_REACH_SPACES * space
    if head_edge is not None:
        lim = head_edge - sign * 0.1 * space
        yb = min(yb, lim) if sign > 0 else max(yb, lim)
    y0_, y1_ = (ya, yb) if ya <= yb else (yb, ya)
    iy0, iy1 = max(0, int(round(y0_))), min(H, int(round(y1_)))
    bx0 = int(round(x1 + G.STEM_TIP_HOOKS_NEAR_SPACES * space))
    bx1 = int(round(x1 + G.STEM_TIP_HOOKS_FAR_SPACES * space))
    cx1 = min(W, int(round(x1 + 1.0 * space)))            # the component reaches 1.0 space out so a line is seen
    lx0 = max(0, int(round(x0 - G.STEM_TIP_HOOKS_LEFT_SPACES * space)))
    lx1 = int(round(x0 - G.STEM_TIP_HOOKS_NEAR_SPACES * space))
    if iy1 - iy0 < 3 or bx1 - bx0 < 3 or lx1 <= lx0 or bx0 >= W:
        return None
    if (iy1 - iy0) < 1.2 * space:
        return {"hooks": None, "reason": "no_room"}
    ink = (img[iy0:iy1, lx0:cx1] == 0).astype(np.uint8)
    k = max(1, int(round(G.STEM_TIP_HOOKS_CLOSE_SPACES * space)))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    _n, lab = cv2.connectedComponents(ink, connectivity=8)
    sc0 = max(0, int(round(x0)) - lx0)
    sc1 = min(ink.shape[1], int(round(x1)) - lx0 + 1)
    seeds = set(np.unique(lab[:, sc0:sc1]).tolist()) - {0}
    if not seeds:
        return {"hooks": None, "reason": "too_little_ink"}
    comp = np.isin(lab, list(seeds))
    xs = np.arange(lx0, cx1)
    us = (xs - x1) / space
    ul = (x0 - xs) / space
    right = comp & (us[None, :] > 0.04)
    left = comp & (ul[None, :] > 0.04)

    def fill(m, u, lo, hi):
        cols = (u >= lo) & (u <= hi)
        return m[:, cols].mean(axis=1) if cols.any() else np.zeros(m.shape[0])
    both = (fill(right, us, 0.04, SH.NEAR_U) >= SH.LINE_FILL) & (fill(left, ul, 0.04, SH.NEAR_U) >= SH.LINE_FILL)
    far_side = (fill(right, us, SH.NEAR_U, SH.FAR_U) >= SH.LINE_FILL) | (fill(left, ul, SH.NEAR_U, SH.FAR_U) >= SH.LINE_FILL)
    on_line = both & far_side
    on_line = on_line | np.roll(on_line, 1) | np.roll(on_line, -1)
    keep = ~on_line
    ncols_left = lx1 - lx0
    left_c = left[:, :ncols_left] & keep[:, None]
    tmin = max(2, int(round(G.STEM_TIP_HOOKS_MIN_THICK_SPACES * space)))
    gmin = max(2, int(round(G.STEM_TIP_HOOKS_MIN_GAP_SPACES * space)))
    near_left = left_c[:, max(0, left_c.shape[1] - int(round(G.STEM_TIP_HOOKS_FAR_SPACES * space))):]
    left_cols = sum(1 for cx in range(near_left.shape[1])
                    if any(r[1] - r[0] >= tmin for r in G._runs_true(near_left[:, cx]))) if near_left.size else 0
    if left_c.size and (float(left_c.sum()) / float(left_c.size) > G.STEM_TIP_HOOKS_LEFT_MAX
                        or left_cols > 0.3 * near_left.shape[1]):
        return {"hooks": None, "reason": "crosses_both_sides"}
    band = comp[:, bx0 - lx0:bx1 - lx0] & keep[:, None]
    ks, starts = [], []
    for cx in range(band.shape[1]):
        merged = []
        for r in G._runs_true(band[:, cx]):
            if r[1] - r[0] < tmin:
                continue
            if merged and r[0] - merged[-1][1] < gmin:
                merged[-1] = (merged[-1][0], r[1])
            else:
                merged.append(r)
        ks.append(len(merged))
        if sign > 0:
            starts.append([(iy0 + a - tip_y) / space for a, _b in merged])
        else:
            starts.append(sorted((tip_y - (iy0 + b)) / space for _a, b in merged))
    inked = [n for n in ks if n > 0]
    if len(inked) < G.STEM_TIP_HOOKS_MIN_COVERAGE * len(ks):
        return {"hooks": None, "reason": "too_little_ink"}
    support = [sum(1 for n in inked if n >= j) / float(len(inked)) for j in (1, 2, 3, 4)]
    count = max(j for j in (1, 2, 3, 4) if support[j - 1] >= G.STEM_TIP_HOOKS_SUPPORT)
    over = support[count] if count < 4 else 0.0
    shaped = True
    if count >= 2:
        cols = sorted((c for c in starts if len(c) >= count), key=lambda c: c[0])
        firsts = sorted(c[0] for c in cols)
        gaps = sorted(c[j] - c[j - 1] for c in cols for j in range(1, count))
        mid = len(cols) // 2
        shaped = (firsts[mid] <= G.STEM_TIP_HOOKS_FIRST_MAX_SPACES
                  and G.STEM_TIP_HOOKS_SPACING_MIN <= gaps[len(gaps) // 2] <= G.STEM_TIP_HOOKS_SPACING_MAX)
    if over > G.STEM_TIP_HOOKS_GLITCH or count >= G.STEM_TIP_HOOKS_MAX_LEVEL + 1 or not shaped:
        return {"hooks": None, "reason": "unresolved", "support": [round(s, 2) for s in support]}
    return {"hooks": count, "support": [round(s, 2) for s in support]}


def main():
    T, cells, rows = build(sys.argv[1])
    out = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["cv"] is None or r["label"] != "flag":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        from tools.omr.staged import gather as G
        heads = [(a, b, c_ - a, d - b) for a, b, c_, d in head_edges_canonical(T, c)]
        edge, here = G._head_edge_for_end(heads, x, x + w, tip_y, sign, s)
        img = (~c["img"]).astype("uint8") * 255
        old = G.stem_tip_hooks(img, x, x + w, tip_y, sign, s, head_edge=edge)
        new = hooks_masked(img, x, x + w, tip_y, sign, s, head_edge=edge)
        ko = "None" if old is None else (f"hooks={old['hooks']}" if old["hooks"] else old["hooks_reason"])
        kn = "None" if new is None else (f"hooks={new['hooks']}" if new["hooks"] else new["reason"])
        out["old"][ko] += 1
        out["new"][kn] += 1
        print(r["stem"], "old:", ko, " new:", kn, new.get("support") if new else None)
    for k, v in out.items():
        print(k, dict(v))


if __name__ == "__main__":
    main()
