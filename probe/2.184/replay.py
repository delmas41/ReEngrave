"""2.184 Part 1 probe (GATHER-only, writes nothing to a record): re-run the PRODUCTION detector (class-wise NMS, iou 0.7, imgsz_for_cell, the record's
weights) on whole pages at a 0.05 floor and keep every rest-class box in page px. Production keeps >= 0.25; so the same run shows what sat under
the floor on the same ink. Also runs agnostic_nms=True to price a class-agnostic merge.
usage: replay.py lit|bra PAGE[,PAGE...] OUT.json"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.measure_extractor import extract_measures
from tools.omr.staged.gather import _system_local
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
W = str(ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
plate, pages, out = sys.argv[1], [int(p) for p in sys.argv[2].split(",")], sys.argv[3]
det = YoloDetector(W)
res = {}
for p in pages:
    t = time.time()
    pws = detect_staves(render_page(PDF[plate], p, dpi=600))
    cells = extract_measures(pws)
    local = _system_local(pws.staves)
    rows = []
    for c in cells:
        k = local.get(c.staff_index)
        x0, y0 = c.bbox_page_px[0], c.bbox_page_px[1]
        up = c.upscale_factor
        staff = next(s for s in pws.staves if s.staff_index == c.staff_index)
        imgsz = imgsz_for_cell(c); hh, ww = c.image.shape[:2]
        shown = staff.line_spacing_px * up * imgsz / max(hh, ww)
        cellbox = [float(v) for v in c.bbox_page_px]
        for ag in (False, True):
            for d in det.detect(c, conf_threshold=0.05, agnostic_nms=ag):
                if not d.smufl_name.startswith("rest"):
                    continue
                rows.append(dict(ag=ag, cls=d.smufl_name, conf=round(d.confidence, 4), key=list(k) + [c.measure_index] if k else None, sp=staff.line_spacing_px,
                                 bbox=[x0 + d.x_canonical / up, y0 + d.y_canonical / up, x0 + (d.x_canonical + d.width_canonical) / up, y0 + (d.y_canonical + d.height_canonical) / up],
                                 staff_top=float(staff.line_ys[0]), staff_bot=float(staff.line_ys[4]), shown_sp=round(shown, 2), imgsz=imgsz, cell=cellbox))
    res[p] = rows
    print(plate, p, len(cells), "cells", len(rows), "rest rows", round(time.time() - t), "s", flush=True)
    json.dump(res, open(out, "w"))
