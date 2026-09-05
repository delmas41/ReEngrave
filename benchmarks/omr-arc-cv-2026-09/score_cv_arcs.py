"""Score the classical-CV arc reader against the adjudicated human boxes —
the same protocol as probe_arcs_vs_human.py (IoU 0.3), so the numbers sit
beside production's recall 0.824 / precision 0.232 / kind 0.717.

Also reports how many of the 260 certified FAKE boxes the reader fires on,
split by the two fake families (proxied by band position: a fake whose centre
is inside the five-line band is the staff-jag family; outside it is the
neighbouring-staff bleed family).
"""
import json
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr.arc_detection import detect_arcs  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
ARC = {"tie", "slur"}


def iou(a, b):
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


class _Cell:
    def __init__(s, ys, im, im_ns):
        s.staff_line_ys_canonical = ys
        s.image = im
        s.image_no_staff = im_ns


def load_boxes():
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


def main():
    truth, fakes = load_boxes()
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    tp = fp = fn = kind_ok = n_det = 0
    fake_fired = {"jag_in_band": 0, "bleed_outside": 0}
    fake_total = {"jag_in_band": 0, "bleed_outside": 0}
    t0 = time.time()
    n_cells = 0
    for cid, tb in truth.items():
        e = mans.get(cid)
        img = cv2.imread(str(B / "cells" / f"{cid}.png"))
        img_ns = cv2.imread(str(B / "cells" / f"{cid}_nostaff.png"),
                            cv2.IMREAD_GRAYSCALE)
        if e is None or img is None:
            continue
        n_cells += 1
        ys = e.get("staff_line_ys_canonical") or []
        cell = _Cell(ys, img, img_ns)
        preds = [(d.smufl_name,
                  (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical))
                 for d in detect_arcs(cell)]
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
            else:
                fn += 1
        fp += len(preds) - len(used)
        # which certified fakes did we fire on?
        top, bot = (min(ys), max(ys)) if len(ys) >= 2 else (0, 10**9)
        for cls, b in fakes.get(cid, []):
            yc = b[1] + b[3] / 2.0
            fam = "jag_in_band" if top <= yc <= bot else "bleed_outside"
            fake_total[fam] += 1
            if any(iou(b, pb) >= 0.3 for _pc, pb in preds):
                fake_fired[fam] += 1
    dt = time.time() - t0
    nt = sum(len(v) for v in truth.values())
    print(json.dumps(dict(
        dets=n_det, tp=tp, fp=fp, fn=fn,
        recall=round(tp / nt, 3), precision=round(tp / max(1, tp + fp), 3),
        kind_acc=round(kind_ok / max(1, tp), 3),
        fake_fired=fake_fired, fake_total=fake_total,
        ms_per_cell=round(1000 * dt / max(1, n_cells), 1),
    ), indent=1))


if __name__ == "__main__":
    main()
