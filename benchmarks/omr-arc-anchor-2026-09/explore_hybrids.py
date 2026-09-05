"""Exploration: hybrid arms (band-conditional anchor/veto), plus the
recovered-vs-veto bookkeeping the round brief asks for. Reuses the caches."""
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr import arc_detection as ad  # noqa: E402
from score_anchor_arms import (  # noqa: E402
    load_truth_fakes, iou, confirmed, _Cell, B, A)


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
                return True
            return ad.arc_box_anchored(box, nh_boxes, nh_w, sp, cell_w,
                                       require_both=both)

        def in_band(box, ys=ys):
            yc = box[1] + box[3] / 2.0
            return bool(ys) and min(ys) <= yc <= max(ys)

        per_cell[cid] = dict(cv=cv_preds, cvr=cv_relaxed, y=y_preds,
                             anch=anch, in_band=in_band)

    def arm(build, name):
        tp = fp = kind_ok = n_det = 0
        fake_fired = jag_fired = bleed_fired = 0
        matched_real = set()
        for cid, tb in truth.items():
            if cid not in per_cell:
                continue
            pc = per_cell[cid]
            preds = build(pc)
            n_det += len(preds)
            used = set()
            for ti, (cls, b) in enumerate(tb):
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
                    matched_real.add((cid, ti))
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
        print(f"{name:22s} dets={n_det:3d} recall={tp/nt:.3f} "
              f"prec={tp/max(1,tp+fp):.3f} kind={kind_ok/max(1,tp):.3f} "
              f"fakes={fake_fired} (jag {jag_fired} / bleed {bleed_fired})",
              flush=True)
        return matched_real

    def veto_arm(pc):
        return [p for p in pc["y"] if confirmed(p[1], pc["cv"])]

    def anchor_arm(pc):
        return [p for p in pc["y"] if pc["anch"](p[1])]

    arms = {
        "veto": veto_arm,
        "anchor": anchor_arm,
        # band-conditional: an in-band arc answers to the CV veto (shape
        # closes the jag family); an out-of-band arc answers to its anchors.
        "band: veto|anchor": lambda pc: [
            p for p in pc["y"]
            if (confirmed(p[1], pc["cv"]) if pc["in_band"](p[1])
                else pc["anch"](p[1]))],
        # same, plus in-band arcs may ALSO pass by anchors (union in band)
        "band: (v or a)|anchor": lambda pc: [
            p for p in pc["y"]
            if ((confirmed(p[1], pc["cv"]) or pc["anch"](p[1]))
                if pc["in_band"](p[1]) else pc["anch"](p[1]))],
        # out-of-band arcs must satisfy BOTH
        "band: veto|(v and a)": lambda pc: [
            p for p in pc["y"]
            if (confirmed(p[1], pc["cv"]) if pc["in_band"](p[1])
                else (pc["anch"](p[1]) and confirmed(p[1], pc["cv"])))],
        # anchor with both-ends required (no cut exemption)
        "anchor-both": lambda pc: [p for p in pc["y"]
                                   if pc["anch"](p[1], both=True)],
    }
    matched = {}
    for name, build in arms.items():
        matched[name] = arm(build, name)

    v, a = matched["veto"], matched["anchor"]
    print(f"\nreal arcs veto lost, anchor recovers: {len(a - v)}")
    print(f"real arcs anchor loses, veto keeps:   {len(v - a)}")
    ba = matched["band: veto|anchor"]
    print(f"band-hybrid vs veto: recovers {len(ba - v)}, loses {len(v - ba)}")


if __name__ == "__main__":
    main()
