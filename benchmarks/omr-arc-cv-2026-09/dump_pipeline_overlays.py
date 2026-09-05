"""Save overlays of pipeline cells whose YOLO arcs the CV veto refuses:
nostaff image, thin mask (orange), chained strokes (red), CV arcs (magenta),
YOLO arcs (green=confirmed, yellow=refused). Usage:
    dump_pipeline_overlays.py <pdf> <page_index> <dpi> <out_dir> [max_cells]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.measure_extractor import extract_measures  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell  # noqa: E402
from tools.omr import arc_detection as ad  # noqa: E402

W = "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt"


def main():
    pdf, page_index, dpi, out_dir = (Path(sys.argv[1]), int(sys.argv[2]),
                                     int(sys.argv[3]), Path(sys.argv[4]))
    max_cells = int(sys.argv[5]) if len(sys.argv) > 5 else 8
    out_dir.mkdir(parents=True, exist_ok=True)
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_staves(page)
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    det = YoloDetector(W, device="mps")
    n_done = 0
    for idx, cell in enumerate(cells):
        dets = det.detect(cell, conf_threshold=0.25, imgsz=imgsz_for_cell(cell))
        arcs_y = [d for d in dets if d.smufl_name in ("tie", "slur")]
        if not arcs_y:
            continue
        sp = ad._staff_line_spacing(cell)
        cv = ad.detect_arcs(cell)
        cv_boxes = [ad._box_of(c) for c in cv]

        def ok(b):
            for cb in cv_boxes:
                oy = min(b[1] + b[3], cb[1] + cb[3]) - max(b[1], cb[1])
                if ad._iou(b, cb) >= 0.1 or (oy > 0 and ad._x_overlap_frac(b, cb) >= 0.5):
                    return True
            return False

        refused = [d for d in arcs_y if not ok(ad._box_of(d))]
        if not any(d.confidence >= 0.4 for d in refused):
            continue
        src = cell.image_no_staff if cell.image_no_staff is not None else cell.image
        ink = ad._binary_ink(src)
        thin = ad._thin_run_mask(ink, max(2, int(round(ad.ARC_THIN_RUN_MAX_SPACES * sp))))
        vis = cv2.cvtColor(src if src.ndim == 2 else cv2.cvtColor(src, cv2.COLOR_BGR2GRAY),
                           cv2.COLOR_GRAY2BGR)
        vis[thin] = (255, 128, 0)
        usable, cut = ad._extract_strokes(thin, sp, ad.ARC_EDGE_MARGIN_PX)
        for s in ad._chain_strokes(usable, sp):
            have = ~np.isnan(s.mid)
            if not have.any():
                continue
            ms = s.mid[have]
            cv2.rectangle(vis, (s.x0, int(np.min(ms)) - 3), (s.x1, int(np.max(ms)) + 3),
                          (0, 0, 255), 2)
        for cb in cv_boxes:
            cv2.rectangle(vis, (cb[0], cb[1]), (cb[0] + cb[2], cb[1] + cb[3]),
                          (255, 0, 255), 3)
        for d in arcs_y:
            b = ad._box_of(d)
            col = (0, 200, 0) if ok(b) else (0, 255, 255)
            cv2.rectangle(vis, (b[0], b[1]), (b[0] + b[2], b[1] + b[3]), col, 2)
            cv2.putText(vis, f"{d.smufl_name}{d.confidence:.2f}", (b[0], max(12, b[1] - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)
        # staff lines for reference
        for y in (cell.staff_line_ys_canonical or []):
            cv2.line(vis, (0, int(y)), (40, int(y)), (200, 0, 200), 2)
        cv2.imwrite(str(out_dir / f"cell{idx:03d}.png"), vis)
        n_done += 1
        if n_done >= max_cells:
            break
    print("wrote", n_done)


if __name__ == "__main__":
    main()
