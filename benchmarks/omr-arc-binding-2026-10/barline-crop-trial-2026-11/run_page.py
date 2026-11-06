"""BARLINE-CROP TRIAL, detector arms for ONE page (measure only; changes no production code).

    python3 run_page.py PLATE PAGE OUT.json [--arms A,B,C,B2] [--control-bad]

Prepares the page exactly as the pipeline does (`pipeline.prepare_pages`, dpi 600), loads the weights the pipeline routes (`--weights auto`),
then runs the SAME `YoloDetector.detect` (default conf 0.25, imgsz=None = per-crop `imgsz_for_cell`, i.e. 16 px per staff space, staff lines
intact, `one_ink.merge` after) on:

  A   every cell as the pipeline cuts it (the control: must reproduce the saved record's arc boxes)
  B   one crop per barline between two cells of a staff: `measure_extractor._build_measure_cell` (same vertical pad, same canonical scale rule)
      centred on the barline, width = mean width of the two cells (half a bar each side)
  B2  the same, one bar each side (two bars wide)            [sensitivity]
  C   one crop per staff per system: the whole staff row across the system (`_build_measure_cell` over the staff's cells' full x extent).
      `max_det` is raised to 3000 for C (and B2) only, because ultralytics' default 300 would truncate a whole row; every arm records
      how many boxes it got per call so a saturated call is visible.

Boxes come back in page pixels by `arcs_system._page_box`. Nothing is written but OUT.json.
"""
import argparse
import json
import os
import sys
import time

os.environ.setdefault("OMR_SURYA_KEEP_ALIVE", "0")

PDF = {
    "litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
ROOT = "/Users/seanjohnson/Desktop/ReEngrave/"


def make_detector(weights, max_det=None):
    from tools.omr.yolo_detector import YoloDetector

    class TrialDetector(YoloDetector):
        calls = []

        def _predict(self, **kw):
            if self.max_det:           # the same ultralytics call `detector_cache.predict` makes with no cache, plus max_det
                kw.pop("aux", None)
                kw["max_det"] = self.max_det
                r = self._model.predict(**kw)
            else:
                r = super()._predict(**kw)
            try:
                n = len(r[0].boxes) if r and r[0].boxes is not None else 0
            except Exception:
                n = -1
            self.calls.append(n)
            return r

    d = TrialDetector(weights)
    d.max_det = max_det
    d.calls = []
    return d


def boxes_of(det, cell, dets):
    from tools.omr.staged.arcs_system import _page_box
    out = []
    for d in dets:
        pb = _page_box(cell, d)
        if pb is None:
            continue
        out.append([str(d.smufl_name), round(float(d.confidence), 4)] + [round(float(v), 2) for v in pb])
    return out


def run_cells(det, cells_iter, conf=0.25, imgsz=None, one_ink=True):
    from tools.omr.staged import one_ink as OI
    res = []
    for tag, cell in cells_iter:
        dets = det.detect(cell, conf_threshold=conf, imgsz=imgsz)
        if dets and one_ink and OI.enabled():
            dets = OI.merge(dets)
        res.append(dict(tag=tag, bbox=[float(v) for v in cell.bbox_page_px], boxes=boxes_of(det, cell, dets)))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plate")
    ap.add_argument("page", type=int)
    ap.add_argument("out")
    ap.add_argument("--arms", default="A,B,C")
    ap.add_argument("--control-bad", action="store_true", help="re-detect cells at a WRONG imgsz (1024) to show the control can fail")
    ap.add_argument("--max-cells", type=int, default=0, help="debug: only the first N cells of A/B")
    a = ap.parse_args()
    os.chdir(ROOT + ".claude/worktrees/agent-aca2654680d85413f")
    sys.path.insert(0, os.getcwd())
    pdf = ROOT + PDF[a.plate]
    arms = a.arms.split(",")

    from tools.omr.staged import pipeline
    from tools.omr.staged import weight_routing
    from tools.omr.measure_extractor import _build_measure_cell

    weights, prov, _cls = weight_routing.resolve_staged_weights(pdf, list(range(12)), weights="auto", route_weights=True)
    print("weights:", os.path.basename(weights), (prov or {}).get("verdict", (prov or {}).get("mode")), flush=True)

    t = time.time()
    (pws, cells), = pipeline.prepare_pages(pdf, [a.page], dpi=600)
    t_prep = time.time() - t
    staff_of = {s.staff_index: s for s in pws.staves}
    cells = [c for c in cells if c.staff_index in staff_of]
    by_staff = {}
    for c in cells:
        by_staff.setdefault(c.staff_index, []).append(c)
    for v in by_staff.values():
        v.sort(key=lambda c: c.measure_index)
    out = dict(plate=a.plate, page=a.page, weights=os.path.basename(weights), t_prepare=t_prep, n_cells=len(cells),
               cells=[dict(staff_index=c.staff_index, system_index=c.system_index, measure_index=c.measure_index,
                           bbox=[float(v) for v in c.bbox_page_px], upscale=float(c.upscale_factor)) for c in cells],
               staves={str(i): dict(top=int(s.top_y), bottom=int(s.bottom_y), sp=float(s.line_spacing_px)) for i, s in staff_of.items()},
               arms={})
    cl = cells[:a.max_cells] if a.max_cells else cells

    if "A" in arms:
        det = make_detector(weights)
        t = time.time()
        r = run_cells(det, (((c.staff_index, c.measure_index), c) for c in cl))
        out["arms"]["A"] = dict(t_detect=time.time() - t, n_calls=len(r), max_calls_boxes=max(det.calls or [0]), items=r)
        print("A", len(r), "cells", round(out["arms"]["A"]["t_detect"], 1), "s", flush=True)
        if a.control_bad:
            t = time.time()
            r = run_cells(det, (((c.staff_index, c.measure_index), c) for c in cl[:60]), imgsz=1024)
            out["arms"]["A_badimgsz"] = dict(t_detect=time.time() - t, items=r)

    def straddles(factor):
        for si, cs in by_staff.items():
            st = staff_of[si]
            for c1, c2 in zip(cs, cs[1:]):
                if c2.measure_index != c1.measure_index + 1:
                    continue
                bx = float(c1.bbox_page_px[2])
                w = ((c1.bbox_page_px[2] - c1.bbox_page_px[0]) + (c2.bbox_page_px[2] - c2.bbox_page_px[0])) / 2.0
                x0, x1 = int(round(bx - factor * w)), int(round(bx + factor * w))
                cell = _build_measure_cell(pws, st, c1.system_index, x0, x1, 9000 + c1.measure_index,
                                           dropped_counter_key="n_measure_cells_dropped_too_narrow")
                if cell is None:
                    continue
                cell.__dict__["bar_x"] = bx
                yield (dict(staff_index=si, system_index=c1.system_index, left_cell=c1.measure_index, bar_x=bx), cell)

    for name, factor, md in (("B", 0.5, None), ("B2", 1.0, 3000)):
        if name not in arms:
            continue
        det = make_detector(weights, md)
        t = time.time()
        it = list(straddles(factor))
        if a.max_cells:
            it = it[:a.max_cells]
        r = run_cells(det, it)
        out["arms"][name] = dict(t_detect=time.time() - t, n_calls=len(r), max_calls_boxes=max(det.calls or [0]), items=r)
        print(name, len(r), "crops", round(out["arms"][name]["t_detect"], 1), "s", flush=True)

    if "C" in arms:
        det = make_detector(weights, 3000)
        t = time.time()
        its = []
        for si, cs in by_staff.items():
            st = staff_of[si]
            x0, x1 = min(c.bbox_page_px[0] for c in cs), max(c.bbox_page_px[2] for c in cs)
            cell = _build_measure_cell(pws, st, cs[0].system_index, int(x0), int(x1), 9999)
            if cell is not None:
                ys = cell.staff_line_ys_canonical
                space = (ys[-1] - ys[0]) / (len(ys) - 1)
                # imgsz_for_cell would clamp to 2048 (staff space shown < 16 on a wide row); ask for the SAME 16 px per space instead
                isz = int(round(16.0 * max(cell.image.shape[:2]) / space / 32)) * 32
                its.append((dict(staff_index=si, system_index=cs[0].system_index, canon_w=int(cell.image.shape[1]),
                               scale=float(cell.upscale_factor), imgsz=isz), cell))
        if a.max_cells:
            its = its[:a.max_cells]
        r = [dict(x, imgsz=tag["imgsz"]) for x, tag in zip(
            (run_cells(det, [(t, c)], imgsz=t["imgsz"])[0] for t, c in its), (t for t, _ in its))]
        out["arms"]["C"] = dict(t_detect=time.time() - t, n_calls=len(r), max_calls_boxes=max(det.calls or [0]), items=r)
        print("C", len(r), "strips", round(out["arms"]["C"]["t_detect"], 1), "s; most boxes in one call", max(det.calls or [0]), flush=True)

    json.dump(out, open(a.out, "w"))


if __name__ == "__main__":
    main()
