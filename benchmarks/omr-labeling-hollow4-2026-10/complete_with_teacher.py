"""ROADMAP 2.4b step 1b -- finish the v24 corpus: every one of the 100 batch cells, hollow classes ALL HUMAN,
every other class filled by the production teacher (distill25-style: `build_rehearsal_versions.py --scope all`).

Rules (the same as the distill25 arm production's donor was trained on, plus the hollow rule):
  * the converter wrote only the 48 cells that hold a hollow head; the other 52 are real EMPTY labels ("Sean
    looked, nothing hollow here") and are added here with their image;
  * a teacher box (production scan weights, conf 0.25, the cell's own imgsz) is kept unless a human box
    overlaps it (IoU > 0.2 or centre inside) -- the human's class wins on contested ink;
  * a teacher box of ANY hollow class (noteheadHalf*, noteheadWhole*, noteheadDoubleWhole*) is DROPPED: on this
    batch hollow was swept by a human on every cell, so an unboxed hollow-looking blob (the hole of an 8, a beam
    gap, an ff bowl) is BACKGROUND, which is exactly what the recall/precision trade is about;
  * staff / staffLine never.
Writes labels into data/user-labeled/<version> (its own new directory; no existing version is touched).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
REPO = Path.cwd()
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
PROD = MAIN / "omr-weights" / "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"
NAMES = json.loads((REPO / "tools/omr/training/deepscoresv2_208_classes.json").read_text())
HOLLOW_PREFIX = ("noteheadHalf", "noteheadWhole", "noteheadDoubleWhole")


def iou(a, b):
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    i = ix * iy
    return i / (a[2] * a[3] + b[2] * b[3] - i) if i > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--batch", type=Path, required=True)
    ap.add_argument("--teacher", type=Path, default=PROD)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--device", default="mps")
    a = ap.parse_args()
    import cv2
    from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

    class _Cell:
        def __init__(self, ys, image):
            self.staff_line_ys_canonical = ys
            self.image = image

    vdir = REPO / "data/user-labeled" / a.version
    cells = json.loads((a.batch / "cells.json").read_text())
    det = YoloDetector(str(a.teacher), device=a.device)
    name_to_id = {n: i for i, n in enumerate(NAMES)}
    added, dropped_hollow, over_human = {}, {}, {}
    n_empty = n_human = 0
    for c in cells:
        cid = c["cell_id"]
        src = REPO / c["cell_png_path"]
        dst = vdir / "images" / f"{cid}.png"
        if not dst.exists():
            shutil.copy2(src, dst)
        lp = vdir / "labels" / f"{cid}.txt"
        human = lp.read_text().splitlines() if lp.exists() else []
        if not human:
            n_empty += 1
        n_human += len(human)
        img = cv2.imread(str(src))
        h, w = img.shape[:2]
        hb = []
        for ln in human:
            _c, cx, cy, bw, bh = ln.split()
            cx, cy, bw, bh = float(cx) * w, float(cy) * h, float(bw) * w, float(bh) * h
            hb.append((cx - bw / 2, cy - bh / 2, bw, bh))
        cell = _Cell(c["staff_line_ys_canonical"], img)
        extra = []
        for d in det.detect(cell, conf_threshold=a.conf, imgsz=imgsz_for_cell(cell)):
            cls = d.smufl_name
            if cls in ("staff", "staffLine", "staffline") or cls not in name_to_id:
                continue
            if cls.startswith(HOLLOW_PREFIX):
                dropped_hollow[cls] = dropped_hollow.get(cls, 0) + 1
                continue
            box = (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)
            bx, by = box[0] + box[2] / 2, box[1] + box[3] / 2
            if any(iou(box, b) > 0.2 or (b[0] <= bx <= b[0] + b[2] and b[1] <= by <= b[1] + b[3]) for b in hb):
                over_human[cls] = over_human.get(cls, 0) + 1
                continue
            extra.append(f"{name_to_id[cls]} {bx / w:.6f} {by / h:.6f} {box[2] / w:.6f} {box[3] / h:.6f}")
            added[cls] = added.get(cls, 0) + 1
        lp.write_text("\n".join(human + extra) + ("\n" if human + extra else ""))
    meta = json.loads((vdir / "metadata.json").read_text())
    meta["teacher_completion"] = {
        "teacher": str(a.teacher), "conf": a.conf, "scope": "all, minus every hollow class (human-swept)",
        "cells": len(cells), "cells_with_no_human_box": n_empty, "human_boxes": n_human,
        "teacher_boxes_added": sum(added.values()), "teacher_by_class": dict(sorted(added.items(), key=lambda kv: -kv[1])[:25]),
        "teacher_hollow_boxes_dropped_as_background": dropped_hollow,
        "teacher_boxes_dropped_over_a_human_box": sum(over_human.values())}
    (vdir / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(meta["teacher_completion"], indent=1))
    return 0 if added else 1


if __name__ == "__main__":
    sys.exit(main())
