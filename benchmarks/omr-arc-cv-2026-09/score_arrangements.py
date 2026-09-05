"""Score the CV/YOLO combination arrangements on the gauntlet.

The beam precedent (`rhythm.resolve_rhythms_for_cell`): replace-outright was
measured worse than keep-YOLO-where-no-CV-overlap. Arcs are measured the same
way rather than assumed.

Arms:
    prod          — production YOLO arcs alone (sanity: 0.824 / 0.232)
    cv            — the CV reader alone
    union         — both, YOLO boxes deduped against CV by IoU >= 0.3
    cv+yolo-gap   — CV primary; YOLO arcs kept only where NO CV arc overlaps
                    their x-range (the beam rule verbatim)
    yolo-cv-veto  — YOLO arcs kept only where SOME CV arc overlaps (IoU 0.1
                    or x-overlap >= 0.5); CV used as a confirmation oracle
    veto+cv       — the veto arm plus CV's own arcs (deduped)
"""
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


def x_overlap_frac(a, b):
    ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    return max(0.0, ox) / max(1, min(a[2], b[2]))


def y_overlap(a, b):
    return min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])


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
    def __init__(s, ys, im):
        s.staff_line_ys_canonical = ys
        s.image = im
        s.image_no_staff = im


def confirmed(yb, cv_preds, xov=0.5):
    return any(iou(yb, cb) >= 0.1
               or (x_overlap_frac(yb, cb) >= xov and y_overlap(yb, cb) > 0)
               for _c, cb in cv_preds)


def main():
    truth, fakes = load()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    yolo = json.load(open("benchmarks/omr-arc-cv-2026-09/yolo_arcs_cache.json"))
    per_cell = {}
    for cid in truth:
        e = mans.get(cid)
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"), cv2.IMREAD_GRAYSCALE)
        if e is None or img_ns is None:
            continue
        cv_preds = [(d.smufl_name, (d.x_canonical, d.y_canonical,
                                    d.width_canonical, d.height_canonical))
                    for d in ad.detect_arcs(_Cell(e.get("staff_line_ys_canonical") or [], img_ns))]
        y_preds = [(d["cls"], tuple(d["box"])) for d in yolo.get(cid, [])]
        per_cell[cid] = (cv_preds, y_preds)

    def arm(build):
        tp = fp = kind_ok = n_det = 0
        fake_fired = 0
        for cid, tb in truth.items():
            if cid not in per_cell:
                continue
            cv_preds, y_preds = per_cell[cid]
            preds = build(cv_preds, y_preds)
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

    arms = {
        "prod": lambda cv, y: y,
        "cv": lambda cv, y: cv,
        "union": lambda cv, y: cv + [p for p in y
                                     if not any(iou(p[1], cb) >= 0.3 for _c, cb in cv)],
        "cv+yolo-where-no-x-overlap": lambda cv, y: cv + [
            p for p in y if not any(x_overlap_frac(p[1], cb) >= 0.3 for _c, cb in cv)],
        "yolo-cv-veto": lambda cv, y: [p for p in y if confirmed(p[1], cv)],
        "yolo-cv-veto-xov0.3": lambda cv, y: [p for p in y if confirmed(p[1], cv, 0.3)],
        "yolo-cv-veto-xov0.7": lambda cv, y: [p for p in y if confirmed(p[1], cv, 0.7)],
        "veto0.3+cv-unmatched": lambda cv, y: (
            [p for p in y if confirmed(p[1], cv, 0.3)]
            + [p for p in cv if not any(
                x_overlap_frac(p[1], q[1]) >= 0.3 and y_overlap(p[1], q[1]) > 0
                for q in y)]),
        "veto+cv": lambda cv, y: [p for p in y if confirmed(p[1], cv)] + [
            p for p in cv if not any(iou(p[1], yb) >= 0.3
                                     for yb2 in [q[1] for q in y if confirmed(q[1], cv)]
                                     for yb in [yb2])],
    }
    for name, build in arms.items():
        print(f"{name:30s} {arm(build)}", flush=True)


if __name__ == "__main__":
    main()
