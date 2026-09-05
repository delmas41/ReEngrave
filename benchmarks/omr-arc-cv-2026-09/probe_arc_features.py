"""Measure the feature populations that will (or will not) separate real arcs
from the two certified fake families.

Candidate strokes are extracted with deliberately LOOSE geometry (anything
long-ish and thin-ish), then each is associated with the adjudicated boxes of
`benchmarks/omr-queue-arcs-2026-09`:

    REAL  — a TP/WRONG_CATEGORY/WRONG_BBOX tie/slur box, or an added one (176)
    FAKE  — an FP tie/slur box (260, human-certified)
    OTHER — matched neither (beams, brackets, text, hairpins ...)

For every candidate the probe records the features a CV arc reader could gate
on; the point is to SEE the populations before choosing any constant, per the
house rule (constants are read off gaps, never tuned into overlap).

Association is deliberately generous (x-overlap >= 0.5 of the shorter span and
y-centres within the box) so a real arc whose ink the extractor fragments is
still credited to its box — the probe measures separability, not the final
scorer's IoU.

Also reported: how many REAL boxes attracted no candidate at all — the recall
ceiling of the extraction itself, before any filtering.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")

BATCH = Path("benchmarks/omr-queue-arcs-2026-09")
ARC_CLASSES = {"tie", "slur"}


def load_truth_and_fakes():
    truth, fakes = {}, {}
    for vf in sorted((BATCH / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        cid = v["cell_id"]
        t, f = [], []
        for d in v.get("detections", []):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            b = d.get("human_bbox") or d.get("model_bbox")
            if not b:
                continue
            box = (b["x"], b["y"], b["w"], b["h"])
            if d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ARC_CLASSES:
                t.append((cls, box))
            elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ARC_CLASSES:
                f.append((d["model_predicted_class"], box))
        for a in v.get("added_detections", []):
            if a.get("human_class") in ARC_CLASSES:
                b = a["bbox"]
                t.append((a["human_class"], (b["x"], b["y"], b["w"], b["h"])))
        truth[cid], fakes[cid] = t, f
    return truth, fakes


def thin_run_mask(ink: np.ndarray, max_run: int) -> np.ndarray:
    """Keep only ink pixels whose VERTICAL run is at most `max_run` tall."""
    m = ink > 0
    h, w = m.shape
    # run ids per column: cumulative count of run starts
    starts = m & ~np.vstack([np.zeros((1, w), bool), m[:-1]])
    run_id = np.cumsum(starts.ravel(order="F")).reshape((h, w), order="F")
    run_id[~m] = 0
    n_runs = run_id.max()
    if n_runs == 0:
        return np.zeros_like(m)
    lengths = np.bincount(run_id.ravel(), minlength=n_runs + 1)
    keep = lengths[run_id] <= max_run
    return m & keep & (run_id > 0)


def component_features(comp_mask, x, y, w, h, sp, W, H, staff_ys):
    """Features of one candidate stroke; comp_mask is the component's own
    pixels within its bbox (bool, h x w)."""
    cols = np.arange(w)
    counts = comp_mask.sum(axis=0)
    have = counts > 0
    if have.sum() < 4:
        return None
    ys_sum = (comp_mask * (np.arange(h)[:, None])).sum(axis=0)
    mid = np.full(w, np.nan)
    mid[have] = ys_sum[have] / counts[have]
    xs = cols[have].astype(float)
    ms = mid[have]
    # quadratic fit of the midline
    A = np.vstack([xs**2, xs, np.ones_like(xs)]).T
    coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
    fit = A @ coef
    resid_rms = float(np.sqrt(np.mean((ms - fit) ** 2)))
    a2 = float(coef[0])
    # arc rise: apex deviation from the chord joining the endpoints
    chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
    dev = ms - chord
    rise = float(np.max(np.abs(dev)))
    # same-side consistency: fraction of deviation on the majority side
    pos = float(np.sum(np.clip(dev, 0, None)))
    neg = float(np.sum(np.clip(-dev, 0, None)))
    side_frac = max(pos, neg) / max(1e-6, pos + neg)
    # jaggedness: median |second difference| of the midline over present cols
    if len(ms) >= 5:
        jag = float(np.median(np.abs(np.diff(ms, 2))))
    else:
        jag = 0.0
    # staff-line proximity: fraction of midline within 0.3 sp of a staff line
    near = 0.0
    if staff_ys:
        d = np.min(np.abs((ms[:, None] + y) - np.array(staff_ys)[None, :]), axis=1)
        near = float(np.mean(d <= 0.3 * sp))
    thick = counts[have].astype(float)
    return dict(
        x=int(x), y=int(y), w=int(w), h=int(h),
        w_sp=w / sp, h_sp=h / sp,
        coverage=float(have.mean()),
        t_med_sp=float(np.median(thick)) / sp,
        t_max_sp=float(np.max(thick)) / sp,
        resid_sp=resid_rms / sp,
        a2_px=a2,
        rise_sp=rise / sp,
        side_frac=side_frac,
        jag_sp=jag / sp,
        near_staff=near,
        touch_left=bool(x <= 1), touch_right=bool(x + w >= W - 2),
        touch_top=bool(y <= 1), touch_bottom=bool(y + h >= H - 2),
    )


def candidates_for_cell(img, sp, staff_ys, *, thin_max_sp=0.45, min_w_sp=0.9):
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY_INV)
    thin = thin_run_mask(ink, max(2, int(round(thin_max_sp * sp))))
    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        thin.astype(np.uint8), connectivity=8)
    H, W = ink.shape
    out = []
    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if w < min_w_sp * sp:
            continue
        comp = labels[y:y + h, x:x + w] == i
        f = component_features(comp, x, y, w, h, sp, W, H, staff_ys)
        if f is not None:
            out.append(f)
    return out


def associate(cand, boxes):
    """Index of the box this candidate belongs to, by x-overlap and y."""
    cx0, cx1 = cand["x"], cand["x"] + cand["w"]
    cyc = cand["y"] + cand["h"] / 2.0
    best, best_ov = None, 0.0
    for k, (_cls, (bx, by, bw, bh)) in enumerate(boxes):
        ox = min(cx1, bx + bw) - max(cx0, bx)
        if ox <= 0:
            continue
        frac = ox / min(cand["w"], bw)
        if frac >= 0.5 and by - 10 <= cyc <= by + bh + 10 and frac > best_ov:
            best, best_ov = k, frac
    return best


def main():
    truth, fakes = load_truth_and_fakes()
    mans = {e["cell_id"]: e for e in json.load(open(BATCH / "cells.json"))}
    rows = []
    real_hit = set()
    n_real_boxes = 0
    for cid, tb in truth.items():
        e = mans.get(cid)
        img_path = BATCH / "cells" / f"{cid}_nostaff.png"
        if not img_path.exists():
            img_path = BATCH / "cells" / f"{cid}.png"
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if e is None or img is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        sp = (max(ys) - min(ys)) / 4.0 if len(ys) >= 2 else 84.0
        fb = fakes.get(cid, [])
        n_real_boxes += len(tb)
        for cand in candidates_for_cell(img, sp, ys):
            kt = associate(cand, tb)
            kf = associate(cand, fb)
            if kt is not None:
                cand["group"] = "REAL"
                cand["cls"] = tb[kt][0]
                real_hit.add((cid, kt))
            elif kf is not None:
                cand["group"] = "FAKE"
                cand["cls"] = fb[kf][0]
            else:
                cand["group"] = "OTHER"
            cand["cell"] = cid
            rows.append(cand)
    out = Path("benchmarks/omr-arc-cv-2026-09/arc_features.json")
    json.dump(rows, open(out, "w"), indent=0)
    n = {g: sum(1 for r in rows if r["group"] == g) for g in ("REAL", "FAKE", "OTHER")}
    print("candidates:", len(rows), n)
    print(f"real boxes with >=1 candidate: {len(real_hit)}/{n_real_boxes}")
    # quick per-feature percentiles by group
    feats = ["w_sp", "h_sp", "coverage", "t_med_sp", "resid_sp", "rise_sp",
             "side_frac", "jag_sp", "near_staff"]
    for g in ("REAL", "FAKE", "OTHER"):
        sub = [r for r in rows if r["group"] == g]
        if not sub:
            continue
        print(f"-- {g} (n={len(sub)})")
        for f in feats:
            v = sorted(r[f] for r in sub)
            q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
            print(f"   {f:10s} p5={q(.05):7.3f} p25={q(.25):7.3f} p50={q(.5):7.3f} p75={q(.75):7.3f} p95={q(.95):7.3f}")
        for f in ("touch_top", "touch_bottom", "touch_left", "touch_right"):
            print(f"   {f:12s} {sum(1 for r in sub if r[f])}/{len(sub)}")


if __name__ == "__main__":
    main()
