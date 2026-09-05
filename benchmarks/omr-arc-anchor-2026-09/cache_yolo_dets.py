"""Cache production's NOTEHEAD + tie/slur detections on the 126 gauntlet
cells, so the anchor arms can be scored without re-running the model.

Round 9. The round-8 cache (`omr-arc-cv-2026-09/yolo_arcs_cache.json`) holds
only the arcs; the anchor test needs the cell's noteheads too — the SAME
noteheads the pipeline would see at arbitration time, i.e. after
`_drop_clipped_notehead_fragments` (which runs before `apply_arc_cv` in
`_detections_for_cell`), so the clipped-drop is mirrored here.
"""
import json
import sys
from pathlib import Path

import cv2

sys.path.insert(0, ".")
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402
from tools.omr.transcribe import _drop_clipped_notehead_fragments  # noqa: E402

B = Path("benchmarks/omr-queue-arcs-2026-09")
OUT = Path("benchmarks/omr-arc-anchor-2026-09/yolo_dets_cache.json")
W = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
     "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


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
        dets = det.detect(cell, conf_threshold=0.25, imgsz=imgsz_for_cell(cell))
        dets, n_dropped = _drop_clipped_notehead_fragments(dets, cell)
        rec = {"arcs": [], "noteheads": [], "n_clipped_dropped": n_dropped}
        for d in dets:
            row = dict(cls=d.smufl_name, conf=round(float(d.confidence), 3),
                       box=[int(d.x_canonical), int(d.y_canonical),
                            int(d.width_canonical), int(d.height_canonical)])
            if d.smufl_name in ("tie", "slur"):
                rec["arcs"].append(row)
            elif (d.category or "") == "notehead":
                rec["noteheads"].append(row)
        out[cid] = rec
        print(cid, len(rec["arcs"]), len(rec["noteheads"]), flush=True)
    json.dump(out, open(OUT, "w"))


if __name__ == "__main__":
    main()
