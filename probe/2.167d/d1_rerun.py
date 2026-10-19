"""2.167d probe 1 (GATHER-only experiment, writes NOTHING to a record): re-cut each sampled held bar five ways and run the
PRODUCTION detector (same weights as the record, same conf/iou/nms/imgsz rule) at a 0.05 floor so boxes under the 0.25 floor are kept.
Variants (all via the shipped `_build_measure_cell`, so the vertical pad, canonical scale and imgsz rule are the production ones):
  base   the bar's own cell (control: boxes >= 0.25 must reproduce the record's boxes)
  shiftR / shiftL   the same cell moved half a bar right / left
  wide   half a bar added on each side (2 bars wide)
  system the whole staff extent (the system strip)
usage: d1_rerun.py lit|bra OUT.json [first_n]"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page            # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402
from tools.omr.measure_extractor import extract_measures, _build_measure_cell   # noqa: E402
from tools.omr.staged.gather import _system_local, _page_box   # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell   # noqa: E402

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
WEIGHTS = str(ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")
FLOOR = 0.05

plate, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else None
sample = [tuple(s) for s in json.load(open(str(ROOT) + "/probe/2.167d/data/%s_sample.json" % plate))]
if n:
    sample = sample[:n]
det = YoloDetector(WEIGHTS)
pages = sorted({s[0] for s in sample})
res = {}
t0 = time.time()
for p in pages:
    pws = detect_staves(render_page(PDF[plate], p, dpi=600))
    cells = extract_measures(pws)
    local = _system_local(pws.staves)
    by_staff = {s.staff_index: s for s in pws.staves}
    cell_of = {}
    for c in cells:
        k = local.get(c.staff_index)
        if k:
            cell_of[(k[0], k[1], c.measure_index)] = c
    for idx, (pp, s, st, ci) in enumerate(sample):
        if pp != p:
            continue
        c = cell_of.get((s, st, ci))
        key = "%d/%d/%d/%d" % (pp, s, st, ci)
        if c is None:
            res[key] = dict(idx=idx, error="no cell")
            continue
        staff = by_staff[c.staff_index]
        x0, y0, x1, y1 = c.bbox_page_px
        w = x1 - x0

        def run(cell, tag):
            sz = imgsz_for_cell(cell)
            dets = det.detect(cell, conf_threshold=FLOOR, imgsz=None)
            rows = []
            for d in dets:
                b = _page_box(cell, d)
                rows.append([d.smufl_name, round(d.confidence, 3)] + [round(v, 1) for v in b])
            return dict(imgsz=sz, shape=list(cell.image.shape[:2]), scale=round(cell.upscale_factor, 3),
                        space_shown=round(staff.line_spacing_px * cell.upscale_factor * sz / max(cell.image.shape[:2]), 1),
                        x=[cell.bbox_page_px[0], cell.bbox_page_px[2]], boxes=rows)

        V = {"base": run(c, "base")}
        for tag, (a, b) in dict(shiftR=(x0 + w / 2, x1 + w / 2), shiftL=(x0 - w / 2, x1 - w / 2),
                                wide=(x0 - w / 2, x1 + w / 2),
                                system=(staff.x_start, staff.x_end)).items():
            cc = _build_measure_cell(pws, staff, s, int(a), int(b), ci, max_cell_width=100000)
            if cc is None:
                V[tag] = dict(error="no cell")
                continue
            V[tag] = run(cc, tag)
        res[key] = dict(idx=idx, cell=[x0, y0, x1, y1], spacing=staff.line_spacing_px, lines=[int(v) for v in staff.line_ys],
                        x_start=staff.x_start, x_end=staff.x_end, variants=V)
    print("page", p, "done", round(time.time() - t0), flush=True)
json.dump(res, open(out, "w"))
print("wrote", out, len(res))
