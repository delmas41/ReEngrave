"""ROADMAP 2.307 T2 -- the production detector through three ways of looking, ONE page (measure only; changes no production code).

    python3 benchmarks/page-and-zoom-2026-11/t2_detect_page.py PLATE PAGE OUT.json

Adapted from the 2.273 barline-crop trial (`git show 270fd9f0e:benchmarks/omr-arc-binding-2026-10/barline-crop-trial-2026-11/run_page.py`).
The page is prepared exactly as the pipeline does (`pipeline.prepare_pages`, dpi 600), weights routed as production (`--weights auto`), and
the SAME `YoloDetector.detect` (conf 0.25, iou 0.7, staff lines intact, `one_ink.merge` after; no box splitting, no rescues) is run on:

  cells  every cell as the pipeline cuts it, imgsz=None (= `imgsz_for_cell`, 16 px per staff space) -- today's view
  row    one crop per staff per system over the staff's whole row (`_build_measure_cell`, the cells' own height rule; the 2.273 strip cut),
         explicit imgsz for 16 px per staff space, max_det 3000
  band   sliding staff-band windows: same `_build_measure_cell` height rule, width = the median cell width of that staff row, 50% overlap,
         starting at the row's left end -- NOT aligned to barlines; explicit 16 px per space; max_det 3000

Every box is mapped to page pixels (`arcs_system._page_box`). Nothing is merged here; `t2_score.py` merges ("same class at the same place,
IoU >= 0.5, is one mark") and scores. Wall time of each way is recorded (detector calls only; page preparation once, shared).
"""
import json
import os
import statistics
import sys
import time

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")
ROOT = "/Users/seanjohnson/Desktop/ReEngrave/"
PDF = {
    "litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
MAX_DET = 3000
TARGET = 16.0


def boxes_of(cell, dets):
    from tools.omr.staged.arcs_system import _page_box
    out = []
    for d in dets:
        pb = _page_box(cell, d)
        if pb is None:
            continue
        out.append([str(d.smufl_name), round(float(d.confidence), 4)] + [round(float(v), 2) for v in pb])
    return out


def isz16(cell):
    ys = list(getattr(cell, "staff_line_ys_canonical", None) or ())
    if len(ys) < 2:
        return None
    space = (ys[-1] - ys[0]) / (len(ys) - 1)
    return int(round(TARGET * max(cell.image.shape[:2]) / space / 32.0)) * 32 if space > 0 else None


def run(det, items, explicit, max_det=None):
    from tools.omr.staged import one_ink as OI
    res, ncalls, most = [], 0, 0
    t = time.time()
    for tag, cell in items:
        kw = {}
        if explicit:
            kw["imgsz"] = isz16(cell)
        if max_det:
            kw["max_det"] = max_det
        dets = det.detect(cell, conf_threshold=0.25, **kw)
        ncalls += 1
        most = max(most, len(dets or ()))
        if dets and OI.enabled():
            dets = OI.merge(dets)
        res.append(dict(tag=tag, bbox=[float(v) for v in cell.bbox_page_px], boxes=boxes_of(cell, dets)))
    return dict(t_detect=time.time() - t, n_calls=ncalls, most_boxes_in_a_call=most, items=res)


def main():
    plate, page, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    pdf = ROOT + PDF[plate]
    from tools.omr.staged import pipeline, weight_routing
    from tools.omr.measure_extractor import _build_measure_cell
    from tools.omr.yolo_detector import YoloDetector

    weights, prov, _ = weight_routing.resolve_staged_weights(pdf, list(range(12)), weights="auto", route_weights=True)
    t = time.time()
    (pws, cells), = pipeline.prepare_pages(pdf, [page], dpi=600)
    t_prep = time.time() - t
    staff_of = {s.staff_index: s for s in pws.staves}
    cells = [c for c in cells if c.staff_index in staff_of]
    by_staff = {}
    for c in cells:
        by_staff.setdefault(c.staff_index, []).append(c)
    for v in by_staff.values():
        v.sort(key=lambda c: c.measure_index)
    out = dict(plate=plate, page=page, weights=os.path.basename(weights), t_prepare=t_prep,
               staves={str(i): dict(top=int(s.top_y), bottom=int(s.bottom_y), sp=float(s.line_spacing_px),
                                    line_ys=[float(y) for y in getattr(s, "line_ys", ())]) for i, s in staff_of.items()},
               ways={})
    det = YoloDetector(weights)

    out["ways"]["cells"] = run(det, [(dict(staff_index=c.staff_index, system_index=c.system_index, measure_index=c.measure_index), c)
                                     for c in cells], explicit=False)
    print("cells", len(cells), round(out["ways"]["cells"]["t_detect"], 1), "s", flush=True)

    rows, bands = [], []
    for si, cs in by_staff.items():
        st = staff_of[si]
        x0, x1 = int(min(c.bbox_page_px[0] for c in cs)), int(max(c.bbox_page_px[2] for c in cs))
        row = _build_measure_cell(pws, st, cs[0].system_index, x0, x1, 9999)
        if row is not None and getattr(row, "image", None) is not None:
            rows.append((dict(staff_index=si, system_index=cs[0].system_index), row))
        w = statistics.median([c.bbox_page_px[2] - c.bbox_page_px[0] for c in cs])
        step = max(1.0, w / 2.0)
        xa, k = float(x0), 0
        while True:
            xb = min(float(x1), xa + w)
            b = _build_measure_cell(pws, st, cs[0].system_index, int(xa), int(round(xb)), 8000 + k)
            if b is not None and getattr(b, "image", None) is not None:
                bands.append((dict(staff_index=si, system_index=cs[0].system_index, k=k, x0=xa, x1=xb), b))
            if xb >= x1:
                break
            xa += step
            k += 1
    out["ways"]["row"] = run(det, rows, explicit=True, max_det=MAX_DET)
    print("row", len(rows), round(out["ways"]["row"]["t_detect"], 1), "s", flush=True)
    out["ways"]["band"] = run(det, bands, explicit=True, max_det=MAX_DET)
    print("band", len(bands), round(out["ways"]["band"]["t_detect"], 1), "s", flush=True)
    json.dump(out, open(outp, "w"))


if __name__ == "__main__":
    main()
