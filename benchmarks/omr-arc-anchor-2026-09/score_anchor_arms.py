"""Score the round-9 anchor arrangements on the gauntlet, beside every
round-8 arm (reproduced from the same caches so the comparison is same-code).

Protocol identical to round 8's `score_arrangements.py`: IoU >= 0.3 against
the adjudicated human boxes, production YOLO at conf 0.25 (cached), CV arcs
computed live from the nostaff PNGs. Extra columns: the fake split (jag /
bleed) per arm, and for the anchor arms the recovered-vs-veto bookkeeping.
"""
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr import arc_detection as ad  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
A = Path("benchmarks/omr-arc-anchor-2026-09")
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


def load_truth_fakes():
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
    truth, fakes = load_truth_fakes()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    cache = json.load(open(A / "yolo_dets_cache.json"))
    per_cell = {}
    for cid in truth:
        e, c = mans.get(cid), cache.get(cid)
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"),
                            cv2.IMREAD_GRAYSCALE)
        if e is None or c is None or img_ns is None:
            continue
        ys = e.get("staff_line_ys_canonical") or []
        cell = _Cell(ys, img_ns)
        cv_preds = [(d.smufl_name, (d.x_canonical, d.y_canonical,
                                    d.width_canonical, d.height_canonical))
                    for d in ad.detect_arcs(cell)]
        cv_relaxed = [(d.smufl_name, (d.x_canonical, d.y_canonical,
                                      d.width_canonical, d.height_canonical))
                      for d in ad.detect_arcs(
                          cell, min_rise_spaces=ad.ARC_RELAXED_MIN_RISE_SPACES)]
        y_preds = [(d["cls"], tuple(d["box"])) for d in c["arcs"]]
        sp = (max(ys) - min(ys)) / (len(ys) - 1) if len(ys) >= 2 else 0.0
        nh_boxes = [tuple(n["box"]) for n in c["noteheads"]]
        nh_w = ad._median_notehead_width(nh_boxes, sp)
        cell_w = e["cell_canonical_w"]

        def anch(box, both=False, nh_boxes=nh_boxes, nh_w=nh_w, sp=sp,
                 cell_w=cell_w):
            if sp <= 1.0:
                return True  # abstain-whole, as the pipeline does
            return ad.arc_box_anchored(box, nh_boxes, nh_w, sp, cell_w,
                                       require_both=both)
        per_cell[cid] = dict(cv=cv_preds, cvr=cv_relaxed, y=y_preds, anch=anch)

    def arm(build):
        tp = fp = kind_ok = n_det = 0
        fake_fired = jag_fired = bleed_fired = 0
        for cid, tb in truth.items():
            if cid not in per_cell:
                continue
            pc = per_cell[cid]
            preds = build(pc)
            n_det += len(preds)
            used = set()
            for cls, b in tb:
                best = None
                for j, (pcls, pb) in enumerate(preds):
                    if j in used:
                        continue
                    o = iou(b, pb)
                    if o >= 0.3 and (best is None or o > best[0]):
                        best = (o, j, pcls)
                if best:
                    used.add(best[1])
                    tp += 1
                    kind_ok += best[2] == cls
            fp += len(preds) - len(used)
            ys = mans[cid].get("staff_line_ys_canonical") or []
            for _c, b in fakes.get(cid, []):
                if any(iou(b, pb) >= 0.3 for _p, pb in preds):
                    fake_fired += 1
                    yc = b[1] + b[3] / 2.0
                    if ys and min(ys) <= yc <= max(ys):
                        jag_fired += 1
                    else:
                        bleed_fired += 1
        nt = sum(len(v) for v in truth.values())
        return dict(dets=n_det, recall=round(tp / nt, 3),
                    precision=round(tp / max(1, tp + fp), 3),
                    kind=round(kind_ok / max(1, tp), 3),
                    fakes=fake_fired, jag=jag_fired, bleed=bleed_fired)

    def veto_arm(pc):
        return [p for p in pc["y"] if confirmed(p[1], pc["cv"])]

    def anchor_arm(pc):
        return [p for p in pc["y"] if pc["anch"](p[1])]

    def anchor_cv_arm(pc):
        kept = anchor_arm(pc)
        kept_boxes = [p[1] for p in kept]
        extra = [p for p in pc["cvr"]
                 if pc["anch"](p[1], both=True)
                 and not any(iou(p[1], kb) >= 0.3 for kb in kept_boxes)]
        return kept + extra

    arms = {
        "prod": lambda pc: pc["y"],
        "cv": lambda pc: pc["cv"],
        "veto (r8)": veto_arm,
        "veto+cv (r8)": lambda pc: veto_arm(pc) + [
            p for p in pc["cv"]
            if not any(iou(p[1], q[1]) >= 0.3 for q in veto_arm(pc))],
        "anchor": anchor_arm,
        "anchor+cv": anchor_cv_arm,
        "anchor AND veto": lambda pc: [p for p in pc["y"]
                                       if pc["anch"](p[1])
                                       and confirmed(p[1], pc["cv"])],
        "anchor OR veto": lambda pc: [p for p in pc["y"]
                                      if pc["anch"](p[1])
                                      or confirmed(p[1], pc["cv"])],
        "anchorAND+cv": lambda pc: (
            [p for p in pc["y"] if pc["anch"](p[1]) and confirmed(p[1], pc["cv"])]
            + [p for p in pc["cvr"]
               if pc["anch"](p[1], both=True)
               and not any(iou(p[1], q[1]) >= 0.3 for q in pc["y"]
                           if pc["anch"](q[1]) and confirmed(q[1], pc["cv"]))]),
    }
    results = {}
    for name, build in arms.items():
        results[name] = arm(build)
        print(f"{name:18s} {results[name]}", flush=True)
    json.dump(results, open(A / "gauntlet_arms.json", "w"), indent=1)


if __name__ == "__main__":
    main()
