"""Population probe for the quadratic-curvature rise (chord-independent):

    curve_rise_sp = |a2| * w^2 / 8 / sp

— the deviation a pure parabola of the fitted curvature would show over the
stroke's own width. Unlike chord rise it does not collapse on HALF arcs (an
arc cut at the barline or the crop), which chord rise under-reads ~4x.

Groups: chained strokes associated (loose x-overlap) to REAL / FAKE boxes,
else OTHER. Also reports the edge-slice geometry for strokes touching the
top/bottom crop edge: the distance of each stroke END below/above the touched
edge — a real arc GRAZES with its apex (both ends well inside), a sliced
neighbour-staff arc EXITS through the edge (an end at the edge).
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


def main():
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    rows = []
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
                tb.append(box)
            elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ARC:
                fb.append(box)
        for a in v.get("added_detections", []):
            if a.get("human_class") in ARC:
                bb = a["bbox"]
                tb.append((bb["x"], bb["y"], bb["w"], bb["h"]))
        e = mans.get(cid)
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"), cv2.IMREAD_GRAYSCALE)
        if e is None or img_ns is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        sp = (max(ys) - min(ys)) / 4.0 if len(ys) >= 2 else 84.0
        _, ink = cv2.threshold(img_ns, 180, 255, cv2.THRESH_BINARY_INV)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        # NO edge sorting here — we want every stroke, cut ones included.
        num, labels, stats, _ = cv2.connectedComponentsWithStats(
            thin.astype(np.uint8), connectivity=8)
        H, W = ink.shape
        strokes = []
        min_w = max(3, int(round(ad.ARC_FRAGMENT_MIN_WIDTH_SPACES * sp)))
        for i in range(1, num):
            x, y, w, h, _a = stats[i]
            if w < min_w:
                continue
            comp = labels[y:y + h, x:x + w] == i
            cnt = comp.sum(axis=0).astype(float)
            have = cnt > 0
            mid = np.full(w, np.nan)
            ys_sum = (comp * np.arange(h)[:, None]).sum(axis=0)
            mid[have] = ys_sum[have] / cnt[have] + y
            strokes.append(ad._Stroke(int(x), int(w), mid, cnt))
        strokes = ad._chain_strokes(strokes, sp)
        for s in strokes:
            have = ~np.isnan(s.mid)
            if have.sum() < 4 or s.width < 0.9 * sp:
                continue
            xs = np.flatnonzero(have).astype(float)
            ms = s.mid[have]
            A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
            coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
            resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
            curve_rise = abs(coef[0]) * s.width ** 2 / 8.0
            chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
            dev = ms - chord
            rise = float(np.max(np.abs(dev)))
            y0 = float(np.min(ms))
            y1 = float(np.max(ms))
            bbox = (s.x0, int(y0), s.width, max(1, int(y1 - y0)))
            grp = "OTHER"
            for box in tb:
                ox = min(bbox[0] + bbox[2], box[0] + box[2]) - max(bbox[0], box[0])
                yc = bbox[1] + bbox[3] / 2.0
                if ox > 0 and ox / min(bbox[2], box[2]) >= 0.5 and box[1] - 10 <= yc <= box[1] + box[3] + 10:
                    grp = "REAL"
                    break
            if grp == "OTHER":
                for box in fb:
                    ox = min(bbox[0] + bbox[2], box[0] + box[2]) - max(bbox[0], box[0])
                    yc = bbox[1] + bbox[3] / 2.0
                    if ox > 0 and ox / min(bbox[2], box[2]) >= 0.5 and box[1] - 10 <= yc <= box[1] + box[3] + 10:
                        grp = "FAKE"
                        break
            touches_top = y0 <= ad.ARC_EDGE_MARGIN_PX + 1
            touches_bot = y1 >= H - ad.ARC_EDGE_MARGIN_PX - 2
            end_l = s.end_y(True, sp)
            end_r = s.end_y(False, sp)
            end_edge_dist = None
            if touches_top and not np.isnan(end_l) and not np.isnan(end_r):
                end_edge_dist = min(end_l, end_r) / sp
            elif touches_bot and not np.isnan(end_l) and not np.isnan(end_r):
                end_edge_dist = (H - max(end_l, end_r)) / sp
            rows.append(dict(grp=grp, w_sp=s.width / sp, rise_sp=rise / sp,
                             curve_sp=curve_rise / sp, resid_sp=resid / sp,
                             touch_tb=bool(touches_top or touches_bot),
                             end_edge_dist=end_edge_dist))
    for g in ("REAL", "FAKE", "OTHER"):
        sub = [r for r in rows if r["grp"] == g]
        print(f"-- {g} n={len(sub)}")
        for f in ("curve_sp", "rise_sp", "resid_sp"):
            v = sorted(r[f] for r in sub)
            if not v:
                continue
            q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
            print(f"   {f:9s} p5={q(.05):6.3f} p25={q(.25):6.3f} p50={q(.5):6.3f} p75={q(.75):6.3f} p95={q(.95):6.3f}")
        tb_sub = [r for r in sub if r["touch_tb"] and r["end_edge_dist"] is not None]
        if tb_sub:
            v = sorted(r["end_edge_dist"] for r in tb_sub)
            q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
            print(f"   touch_tb n={len(tb_sub)} end_edge_dist p5={q(.05):.2f} p25={q(.25):.2f} p50={q(.5):.2f} p75={q(.75):.2f} p95={q(.95):.2f}")


if __name__ == "__main__":
    main()
