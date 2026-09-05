"""Cache production's tie/slur detections on the 126 gauntlet cells, so the
arrangement arms (union / veto / keep-where-no-overlap) can be scored without
re-running the model."""
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"


class _Cell:
    def __init__(s, ys, im):
        s.staff_line_ys_canonical = ys
        s.image = im


def main():
    mans = {e["cell_id"]: e for e in json.load(open(B / "cells.json"))}
    det = YoloDetector(W, device="mps")
    out = {}
    for cid, e in mans.items():
        img = cv2.imread(str(B / "cells" / f"{cid}.png"))
        if img is None:
            continue
        cell = _Cell(e.get("staff_line_ys_canonical") or [], img)
        out[cid] = [
            dict(cls=d.smufl_name, conf=round(float(d.confidence), 3),
                 box=[int(d.x_canonical), int(d.y_canonical),
                      int(d.width_canonical), int(d.height_canonical)])
            for d in det.detect(cell, conf_threshold=0.25,
                                imgsz=imgsz_for_cell(cell))
            if d.smufl_name in ("tie", "slur")
        ]
        print(cid, len(out[cid]), flush=True)
    json.dump(out, open("benchmarks/omr-arc-cv-2026-09/yolo_arcs_cache.json", "w"))


if __name__ == "__main__":
    main()
