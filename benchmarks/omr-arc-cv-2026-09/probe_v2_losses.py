"""v2 diagnosis, both directions, using the module's own pipeline.

Misses: for each truth box, best post-chain stroke IoU; if a gated stroke
matches at IoU>=0.3 but was refused, name the gates.

False positives: for each emitted arc matching no truth box — certified fake
(by family) or "other"; for "other", its position relative to the staff band.
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


def stroke_bbox_and_gates(s, sp):
    """(bbox, failed_gate_names) for one chained stroke, mirroring _gate_stroke."""
    fails = []
    w = s.width
    have = ~np.isnan(s.mid)
    n_cols = int(have.sum())
    if n_cols < 4:
        return None, ["tiny"]
    ms = s.mid[have]
    y0 = float(np.min(ms - s.cnt[have] / 2.0))
    y1 = float(np.max(ms + s.cnt[have] / 2.0))
    bbox = (s.x0, int(round(y0)), w, max(1, int(round(y1 - y0))))
    if w < ad.ARC_MIN_WIDTH_SPACES * sp:
        fails.append("width")
    if n_cols / w < ad.ARC_MIN_COVERAGE:
        fails.append("coverage")
    xs = np.flatnonzero(have).astype(float)
    A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
    coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
    resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
    if resid > ad.ARC_MAX_FIT_RESID_SPACES * sp:
        fails.append("resid")
    chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
    dev = ms - chord
    rise = float(np.max(np.abs(dev)))
    if rise < ad.ARC_MIN_RISE_SPACES * sp:
        fails.append(f"rise({rise/sp:.2f})")
    pos = float(np.sum(np.clip(dev, 0, None)))
    neg = float(np.sum(np.clip(-dev, 0, None)))
    if max(pos, neg) / max(1e-6, pos + neg) < ad.ARC_MIN_SIDE_FRACTION:
        fails.append("side")
    return bbox, fails


def main():
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    miss_out = {}
    fp_out = {}
    fp_other_pos = []
    for vf in sorted((B / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        cid = v["cell_id"]
        tb, fb = [], []
        for d in v.get("detections", []):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            bb = d.get("human_bbox") or d.get("model_bbox")
            if not bb:
                continue
            box = (bb["x"], bb["y"], bb["w"], bb["h"])
            if d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ARC:
                tb.append((cls, box))
            elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ARC:
                fb.append(box)
        for a in v.get("added_detections", []):
            if a.get("human_class") in ARC:
                bb = a["bbox"]
                tb.append((a["human_class"], (bb["x"], bb["y"], bb["w"], bb["h"])))
        e = mans.get(cid)
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"), cv2.IMREAD_GRAYSCALE)
        if e is None or img_ns is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        sp = (max(ys) - min(ys)) / 4.0 if len(ys) >= 2 else 84.0
        top, bot = (min(ys), max(ys)) if len(ys) >= 2 else (0, 10 ** 9)
        _, ink = cv2.threshold(img_ns, 180, 255, cv2.THRESH_BINARY_INV)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        usable, cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
        chained = ad._chain_strokes(usable, sp)
        info = [stroke_bbox_and_gates(s, sp) for s in chained]
        passed = [(bbox, fails) for bbox, fails in info if bbox and not fails]
        # misses
        for cls, box in tb:
            best = max(((iou(box, bbox), fails) for bbox, fails in info if bbox),
                       key=lambda t: t[0], default=(0.0, None))
            if best[0] >= 0.3 and not best[1]:
                k = "matched"
            elif best[0] >= 0.3:
                k = "gate:" + "+".join(best[1])
            else:
                # was it lost to the top/bottom cut refusal?
                cut_best = 0.0
                for s in cut:
                    have = ~np.isnan(s.mid)
                    if not have.any():
                        continue
                    ms = s.mid[have]
                    bb2 = (s.x0, int(np.min(ms)), s.width,
                           max(1, int(np.max(ms) - np.min(ms))))
                    cut_best = max(cut_best, iou(box, bb2))
                k = ("cut_top_bottom" if cut_best >= 0.3
                     else f"iou_low({best[0]:.2f})" if best[0] > 0.05
                     else "no_stroke")
            miss_out[k] = miss_out.get(k, 0) + 1
        # false positives
        used = set()
        for cls, box in tb:
            best = None
            for j, (bbox, _f) in enumerate(passed):
                if j in used:
                    continue
                o = iou(box, bbox)
                if o >= 0.3 and (best is None or o > best[0]):
                    best = (o, j)
            if best:
                used.add(best[1])
        for j, (bbox, _f) in enumerate(passed):
            if j in used:
                continue
            if any(iou(fbx, bbox) >= 0.3 for fbx in fb):
                yc = bbox[1] + bbox[3] / 2.0
                fam = "certified_jag" if top <= yc <= bot else "certified_bleed"
                fp_out[fam] = fp_out.get(fam, 0) + 1
            else:
                yc = bbox[1] + bbox[3] / 2.0
                r = ((yc - top) / sp if yc < top
                     else (yc - bot) / sp if yc > bot else 0.0)
                fp_out["other"] = fp_out.get("other", 0) + 1
                fp_other_pos.append(round(r, 2))
    print("MISSES (of 176):")
    for k, n in sorted(miss_out.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {k}")
    print("FALSE POSITIVES:")
    for k, n in sorted(fp_out.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {k}")
    hist = {}
    for r in fp_other_pos:
        b = ("in_band" if r == 0 else
             f"above_{int(min(6, -r))}" if r < 0 else f"below_{int(min(6, r))}")
        hist[b] = hist.get(b, 0) + 1
    print("  other-FP positions:", dict(sorted(hist.items())))


if __name__ == "__main__":
    main()
