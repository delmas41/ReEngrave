"""On one pipeline page: how many YOLO tie/slur detections exist, and how
many the CV veto confirms — with the near-miss geometry for the unconfirmed
(nearest CV arc's x-overlap / IoU), to see whether the veto is refusing
rightly (phantoms) or wrongly (misaligned confirmation).

Usage: probe_veto_on_page.py <pdf> <page_index> [dpi]
"""
import sys
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402
from tools.omr import arc_detection as ad  # noqa: E402

W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"


def main():
    pdf = Path(sys.argv[1])
    page_index = int(sys.argv[2])
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 600
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    det = YoloDetector(W, device="mps")
    n_y = {"tie": 0, "slur": 0}
    n_conf = {"tie": 0, "slur": 0}
    near = []
    for cell in cells:
        dets = det.detect(cell, conf_threshold=0.25, imgsz=imgsz_for_cell(cell))
        arcs_y = [d for d in dets if d.smufl_name in ("tie", "slur")]
        if not arcs_y:
            continue
        cv = ad.detect_arcs(cell)
        cv_boxes = [ad._box_of(c) for c in cv]
        for d in arcs_y:
            n_y[d.smufl_name] += 1
            b = ad._box_of(d)
            ok = False
            best = (0.0, 0.0)
            for cb in cv_boxes:
                i = ad._iou(b, cb)
                xo = ad._x_overlap_frac(b, cb)
                oy = min(b[1] + b[3], cb[1] + cb[3]) - max(b[1], cb[1])
                if i >= 0.1 or (oy > 0 and xo >= 0.5):
                    ok = True
                best = max(best, (i, xo if oy > 0 else 0.0))
            if ok:
                n_conf[d.smufl_name] += 1
            else:
                near.append((d.smufl_name, round(d.confidence, 2),
                             round(best[0], 2), round(best[1], 2), b))
    print("YOLO arcs:", n_y, " confirmed:", n_conf)
    print("unconfirmed sample (cls, conf, best_iou, best_xov, box):")
    for row in near[:25]:
        print("  ", row)


if __name__ == "__main__":
    main()
