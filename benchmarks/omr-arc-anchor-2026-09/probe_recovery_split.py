"""Class split of the veto-vs-anchor recovery: of the real arcs the round-8
veto lost, how many does the anchor keep, tie vs slur (and the reverse)."""
import json
import sys

import cv2

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arc-anchor-2026-09")
from tools.omr import arc_detection as ad  # noqa: E402
from score_anchor_arms import (  # noqa: E402
    load_truth_fakes, iou, confirmed, _Cell, B, A)


def main():
    truth, _fakes = load_truth_fakes()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    cache = json.load(open(A / "yolo_dets_cache.json"))
    rec = {"tie": 0, "slur": 0}
    lost = {"tie": 0, "slur": 0}
    for cid, tb in truth.items():
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
        y_preds = [(d["cls"], tuple(d["box"])) for d in c["arcs"]]
        sp = (max(ys) - min(ys)) / (len(ys) - 1) if len(ys) >= 2 else 0.0
        nh_boxes = [tuple(n["box"]) for n in c["noteheads"]]
        nh_w = ad._median_notehead_width(nh_boxes, sp)
        cw = e["cell_canonical_w"]

        def match(preds):
            used, m = set(), set()
            for ti, (cls, b) in enumerate(tb):
                best = None
                for j, (_pc, pb) in enumerate(preds):
                    if j in used:
                        continue
                    o = iou(b, pb)
                    if o >= 0.3 and (best is None or o > best[0]):
                        best = (o, j)
                if best:
                    used.add(best[1])
                    m.add(ti)
            return m

        veto = [p for p in y_preds if confirmed(p[1], cv_preds)]
        anch = [p for p in y_preds
                if sp > 1.0 and ad.arc_box_anchored(p[1], nh_boxes, nh_w,
                                                    sp, cw)]
        mv, ma = match(veto), match(anch)
        for ti in ma - mv:
            rec[tb[ti][0]] += 1
        for ti in mv - ma:
            lost[tb[ti][0]] += 1
    print("anchor recovers over veto:", rec, " anchor loses vs veto:", lost)


if __name__ == "__main__":
    main()
