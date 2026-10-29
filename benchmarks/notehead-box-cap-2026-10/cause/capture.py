"""2.222 cause, the CONTROL: re-run GATHER on ONE page exactly as production does (dpi 600, weights routed, the shared detector
cache, so no forward pass), and capture the detector's OWN output for every cell call -- ultralytics' xyxy in the cell image,
before our SymbolDetection conversion -- with the cell's page rectangle and scale. STAGED GATHER; changes nothing in tools/.

    OMR_DETECTOR_CACHE=/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/detector-cache \
      python3 benchmarks/notehead-box-cap-2026-10/cause/capture.py litolff 2 OUT_DIR

Writes OUT_DIR/<plate>.p<page>.record.json (the gathered record) and OUT_DIR/<plate>.p<page>.raw.json (one entry per detect call).
"""
import json, pathlib, runpy, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr import yolo_detector as YD   # noqa: E402

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
plate, pg, out = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
CALLS = []
_orig_detect, _orig_predict = YD.YoloDetector.detect, YD.YoloDetector._predict
_cur = {}


def _predict(self, **kw):
    res = _orig_predict(self, **kw)
    try:
        b = res[0].boxes
        names = self._class_names or {}
        _cur["raw"] = [dict(xyxy=[float(v) for v in xy], cls=names.get(int(c), str(int(c))), conf=float(f))
                       for xy, c, f in zip(b.xyxy.cpu().numpy(), b.cls.cpu().numpy(), b.conf.cpu().numpy())]
        _cur["imgsz"] = kw.get("imgsz"); _cur["conf"] = kw.get("conf")
    except Exception as e:                                   # noqa: BLE001
        _cur["raw_error"] = repr(e)
    return res


def _detect(self, cell, *a, **kw):
    _cur.clear()
    dets = _orig_detect(self, cell, *a, **kw)
    CALLS.append(dict(page=cell.page_index, staff=cell.staff_index, measure=cell.measure_index,
                      cell_bbox_page_px=[float(v) for v in cell.bbox_page_px], upscale=float(cell.upscale_factor),
                      image_shape=list(cell.image.shape[:2]), **_cur,
                      dets=[dict(cls=d.smufl_name, x=d.x_canonical, y=d.y_canonical, w=d.width_canonical, h=d.height_canonical,
                                 conf=float(d.confidence)) for d in dets]))
    return dets


YD.YoloDetector.detect, YD.YoloDetector._predict = _detect, _predict
rec = out / ("%s.p%s.record.json" % (plate, pg))
sys.argv = ["tools.omr.staged", str(LIB / PDF[plate]), "--pages", pg, "--dpi", "600", "--weights", "auto", "--route-weights",
            "--through", "gather", "--out", str(rec)]
try:
    runpy.run_module("tools.omr.staged", run_name="__main__")
except SystemExit:
    pass
(out / ("%s.p%s.raw.json" % (plate, pg))).write_text(json.dumps(CALLS))
print("detect calls", len(CALLS))
