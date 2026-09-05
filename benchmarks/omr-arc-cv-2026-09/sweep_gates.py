"""Sweep the arc reader's constants on the gauntlet, one arm per config.

Reports recall / precision / kind / fakes-fired per arm, so plateaus are
visible and each shipped constant can be shown to sit on one.
"""
import itertools
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr import arc_detection as ad  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
ARC = {"tie", "slur"}


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


def load():
    truth, fakes = {}, {}
    for vf in sorted((B / "verdicts").glob("*.verdict.json")):
        v = json.loads(vf.read_text())
        t, f = [], []
        for d in v.get("detections", []):
            cls = d.get("human_corrected_class") or d.get("model_predicted_class")
            bb = d.get("human_bbox") or d.get("model_bbox")
            if not bb:
                continue
            box = (bb["x"], bb["y"], bb["w"], bb["h"])
            if d.get("verdict") in ("TP", "WRONG_CATEGORY", "WRONG_BBOX") and cls in ARC:
                t.append((cls, box))
            elif d.get("verdict") == "FP" and d.get("model_predicted_class") in ARC:
                f.append((d["model_predicted_class"], box))
        for a in v.get("added_detections", []):
            if a.get("human_class") in ARC:
                bb = a["bbox"]
                t.append((a["human_class"], (bb["x"], bb["y"], bb["w"], bb["h"])))
        truth[v["cell_id"]], fakes[v["cell_id"]] = t, f
    return truth, fakes


class _Cell:
    def __init__(s, ys, im_ns):
        s.staff_line_ys_canonical = ys
        s.image = im_ns
        s.image_no_staff = im_ns


def run_arm(truth, fakes, mans, images, overrides):
    saved = {k: getattr(ad, k) for k in overrides}
    for k, v in overrides.items():
        setattr(ad, k, v)
    try:
        tp = fp = kind_ok = n_det = 0
        fake_fired = 0
        for cid, tb in truth.items():
            e, img_ns = mans.get(cid), images.get(cid)
            if e is None or img_ns is None:
                continue
            cell = _Cell(e.get("staff_line_ys_canonical") or [], img_ns)
            preds = [(d.smufl_name, (d.x_canonical, d.y_canonical,
                                     d.width_canonical, d.height_canonical))
                     for d in ad.detect_arcs(cell)]
            n_det += len(preds)
            used = set()
            for cls, b in tb:
                best = None
                for j, (pc, pb) in enumerate(preds):
                    if j in used:
                        continue
                    o = iou(b, pb)
                    if o >= 0.3 and (best is None or o > best[0]):
                        best = (o, j, pc)
                if best:
                    used.add(best[1])
                    tp += 1
                    kind_ok += best[2] == cls
            fp += len(preds) - len(used)
            for _c, b in fakes.get(cid, []):
                if any(iou(b, pb) >= 0.3 for _p, pb in preds):
                    fake_fired += 1
        nt = sum(len(v) for v in truth.values())
        return dict(dets=n_det, recall=round(tp / nt, 3),
                    precision=round(tp / max(1, tp + fp), 3),
                    kind=round(kind_ok / max(1, tp), 3), fakes=fake_fired)
    finally:
        for k, v in saved.items():
            setattr(ad, k, v)


def main():
    truth, fakes = load()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    images = {cid: cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"),
                              cv2.IMREAD_GRAYSCALE) for cid in truth}
    arms = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else {
        "v3": {},
    }
    for name, ov in arms.items():
        r = run_arm(truth, fakes, mans, images, ov)
        print(f"{name:40s} {r}", flush=True)


if __name__ == "__main__":
    main()
