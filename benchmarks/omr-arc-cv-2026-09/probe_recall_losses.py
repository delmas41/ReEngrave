"""Where does each REAL arc box get lost?

For every truth box: extract UNGATED thin-mask components (width >= 0.9 sp
only), find the best-IoU component and the best x-overlap component, and
classify the loss:

    matched      — a component passes every gate AND IoU >= 0.3
    gate:<name>  — best-IoU component >= 0.3 but a gate refuses it
    iou_low      — a component covers >= 60% of the box's x-span but IoU < 0.3
                   (fragmentation or tight-vs-generous box mismatch)
    no_candidate — nothing in the thin mask overlaps the box at all
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr import arc_detection as ad  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
ARC = {"tie", "slur"}


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


def gates(comp_mask, x, y, w, h, sp, W, H):
    """Return the list of gate names this candidate fails (empty = passes)."""
    fails = []
    if w < ad.ARC_MIN_WIDTH_SPACES * sp:
        fails.append("width")
    if (x <= ad.ARC_EDGE_MARGIN_PX or y <= ad.ARC_EDGE_MARGIN_PX
            or x + w >= W - ad.ARC_EDGE_MARGIN_PX or y + h >= H - ad.ARC_EDGE_MARGIN_PX):
        fails.append("edge")
    counts = comp_mask.sum(axis=0)
    have = counts > 0
    n_cols = int(have.sum())
    if n_cols < 4:
        return fails + ["tiny"]
    if n_cols / w < ad.ARC_MIN_COVERAGE:
        fails.append("coverage")
    if float(np.median(counts[have])) > ad.ARC_MAX_THICKNESS_SPACES * sp:
        fails.append("thickness")
    ys_sum = (comp_mask * np.arange(h)[:, None]).sum(axis=0)
    xs = np.flatnonzero(have).astype(float)
    ms = ys_sum[have] / counts[have]
    A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
    coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
    resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
    if resid > ad.ARC_MAX_FIT_RESID_SPACES * sp:
        fails.append("resid")
    chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
    dev = ms - chord
    rise = float(np.max(np.abs(dev)))
    if rise < ad.ARC_MIN_RISE_SPACES * sp:
        fails.append("rise")
    pos = float(np.sum(np.clip(dev, 0, None)))
    neg = float(np.sum(np.clip(-dev, 0, None)))
    if max(pos, neg) / max(1e-6, pos + neg) < ad.ARC_MIN_SIDE_FRACTION:
        fails.append("side")
    return fails


def main():
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    outcomes = {}
    details = []
    for vf in sorted((B / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        cid = v["cell_id"]
        tb = []
        for d in v.get("detections", []):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            bb = d.get("human_bbox") or d.get("model_bbox")
            if bb and d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ARC:
                tb.append((cls, (bb["x"], bb["y"], bb["w"], bb["h"])))
        for a in v.get("added_detections", []):
            if a.get("human_class") in ARC:
                bb = a["bbox"]
                tb.append((a["human_class"], (bb["x"], bb["y"], bb["w"], bb["h"])))
        if not tb:
            continue
        e = mans.get(cid)
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"), cv2.IMREAD_GRAYSCALE)
        if e is None or img_ns is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        sp = (max(ys) - min(ys)) / 4.0 if len(ys) >= 2 else 84.0
        _, ink = cv2.threshold(img_ns, 180, 255, cv2.THRESH_BINARY_INV)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        num, labels, stats, _ = cv2.connectedComponentsWithStats(
            thin.astype(np.uint8), connectivity=8)
        H, W = ink.shape
        comps = []
        for i in range(1, num):
            x, y, w, h, _a = stats[i]
            if w < 0.5 * sp:
                continue
            comps.append((int(x), int(y), int(w), int(h), i))
        for cls, box in tb:
            bx, by, bw, bh = box
            best = None       # (iou, comp)
            best_xov = None   # (frac, comp)
            for (x, y, w, h, i) in comps:
                o = iou(box, (x, y, w, h))
                if best is None or o > best[0]:
                    best = (o, (x, y, w, h, i))
                ox = min(x + w, bx + bw) - max(x, bx)
                oy = min(y + h, by + bh) - max(y, by)
                if ox > 0 and oy > -0.5 * sp:
                    frac = ox / bw
                    if best_xov is None or frac > best_xov[0]:
                        best_xov = (frac, (x, y, w, h, i))
            if best is None or best[0] <= 0:
                out = "no_candidate"
            elif best[0] >= 0.3:
                x, y, w, h, i = best[1]
                fails = gates(labels[y:y + h, x:x + w] == i, x, y, w, h, sp, W, H)
                out = "matched" if not fails else "gate:" + "+".join(fails)
            else:
                frac = best_xov[0] if best_xov else 0.0
                out = "iou_low_frag" if frac < 0.6 else "iou_low_shape"
            outcomes[out] = outcomes.get(out, 0) + 1
            details.append(dict(cell=cid, cls=cls, box=box, outcome=out,
                                best_iou=round(best[0], 3) if best else 0.0))
    for k, n in sorted(outcomes.items(), key=lambda kv: -kv[1]):
        print(f"{n:4d}  {k}")
    json.dump(details, open("benchmarks/omr-arc-cv-2026-09/recall_losses.json", "w"), indent=1)


if __name__ == "__main__":
    main()
