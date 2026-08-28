"""Tune the staff-header specialist crop: header fraction x imgsz.

Runs phase-1 once on a page, grabs each staff's start cell, and reads the clef
from crops at several (header_frac, imgsz) settings — comparing each to the
full-cell @1280 reference (which the decoupled run validated) on both agreement
and wall-clock. Picks a setting that keeps clef reads while running cheaper.
"""
import dataclasses
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import (
    detect_barlines, extract_measures, resegment_fused_measures)
from tools.omr.staff_line_removal import remove_staff_lines
from tools.omr.yolo_detector import YoloDetector
from tools.omr.transcribe import _clef_name_from_class
from tools.omr.rhythm import parse_time_signature

PDF = "/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/PDF Scores/Mahler_5_.pdf"
WEIGHTS = "omr-weights/deepscoresv2-yolov8l-clef-ft-boxfix-2026-07-13.pt"
PAGE = int(sys.argv[1]) if len(sys.argv) > 1 else 11


def staff_start_cells(pdf, page_idx):
    page = render_page(Path(pdf), page_idx, dpi=300)
    pws = detect_staves(page)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    cells = resegment_fused_measures(pws, cells)
    remove_staff_lines(cells)
    starts = {}
    for c in cells:
        key = (c.system_index, c.staff_index)
        if key not in starts or c.measure_index < starts[key].measure_index:
            starts[key] = c
    return [starts[k] for k in sorted(starts)]


def read_header(reader, cell, frac, imgsz):
    hw = max(1, int(round(cell.width * frac)))
    cc = dataclasses.replace(cell, image=cell.image[:, :hw], image_no_staff=None)
    dets = reader.detect(cc, conf_threshold=0.30, imgsz=imgsz,
                         iou_threshold=0.5, agnostic_nms=True)
    clefs = [(_clef_name_from_class(d.smufl_name), d.confidence)
             for d in dets if d.category == "clef" and _clef_name_from_class(d.smufl_name)]
    clefs.sort(key=lambda x: -x[1])
    clef = clefs[0][0] if clefs else None
    ts = parse_time_signature(dets)
    return clef, ts


def main():
    starts = staff_start_cells(PDF, PAGE)
    print(f"page {PAGE}: {len(starts)} staff-start cells "
          f"(canonical widths {min(c.width for c in starts)}–{max(c.width for c in starts)})")
    reader = YoloDetector(WEIGHTS, device="auto")

    # reference: full cell @ 1280
    ref = [read_header(reader, c, 1.0, 1280)[0] for c in starts]
    print(f"REFERENCE full@1280 clefs: {dict(Counter(r or '(none)' for r in ref))}")

    print(f"\n{'setting':<18}{'clef agree':>12}{'detected':>10}{'n_timesig':>11}{'time':>9}")
    for frac, imgsz in [(1.0, 1280), (0.42, 1280), (0.42, 1024), (0.42, 768),
                        (0.42, 640), (0.30, 768), (0.30, 640), (0.25, 640)]:
        t = time.perf_counter()
        reads = [read_header(reader, c, frac, imgsz) for c in starts]
        dt = time.perf_counter() - t
        clefs = [r[0] for r in reads]
        agree = sum(1 for a, b in zip(clefs, ref) if a == b)
        ndet = sum(1 for c in clefs if c)
        nts = sum(1 for r in reads if r[1])
        print(f"frac{frac} imgsz{imgsz:<7}{agree:>4}/{len(ref):<7}{ndet:>10}{nts:>11}{dt:>8.1f}s")


if __name__ == "__main__":
    main()
