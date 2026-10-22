"""2.172 probe 1 (GATHER-only, writes NOTHING to a record): run the PRODUCT view code (`tools/omr/staged/detector_views.views_for_cell`) on the
2.167d sample bars (the 45 + 45 held bars of 2.167c, same order), under the parts switched on one at a time.

Per bar: the production detector box set (`YoloDetector.detect`, conf 0.25, = what GATHER hands the views), compared to the 20261018-night
record's detector boxes (CONTROL 1: must agree, and does fail when imgsz is changed -- `--perturb`); then for each variant of the sub-switches
the views' kept and refused boxes, in PAGE pixels, with view, family, median conf, phase confs; wall time of the production call and of each
variant (the cost multiplier).

usage: v1_bars.py lit|bra OUT.json [--perturb] [--first N]"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.preprocessing import render_page            # noqa: E402
from tools.omr.staff_detector import detect_staves          # noqa: E402
from tools.omr.measure_extractor import extract_measures    # noqa: E402
from tools.omr.staged.gather import _system_local           # noqa: E402
from tools.omr.staged import detector_views as DV           # noqa: E402
from tools.omr.yolo_detector import YoloDetector, imgsz_for_cell   # noqa: E402

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
WEIGHTS = str(ROOT / "tools/omr/training/data/weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")

VARIANTS = {          # name -> env (PARTS, PHASES)
    "full": {"OMR_DETECTOR_VIEWS_PARTS": "views,aa,phase"},
    "noaa": {"OMR_DETECTOR_VIEWS_PARTS": "views,phase"},
    "nophase": {"OMR_DETECTOR_VIEWS_PARTS": "views,aa"},
    "bare": {"OMR_DETECTOR_VIEWS_PARTS": "views"},
}


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def page_box(c, d):
    x0, y0 = c.bbox_page_px[0], c.bbox_page_px[1]
    up = c.upscale_factor
    return [round(x0 + d.x_canonical / up, 1), round(y0 + d.y_canonical / up, 1),
            round(x0 + (d.x_canonical + d.width_canonical) / up, 1), round(y0 + (d.y_canonical + d.height_canonical) / up, 1)]


def main():
    plate, out = sys.argv[1], sys.argv[2]
    perturb = "--perturb" in sys.argv
    nmax = int(sys.argv[sys.argv.index("--first") + 1]) if "--first" in sys.argv else None
    sample = [tuple(s) for s in json.load(open(str(ROOT) + "/probe/2.167d/data/%s_sample.json" % plate))]
    rec = json.load(open(str(ROOT) + "/probe/2.167d/data/%s_rec.json" % plate))["cells"]
    keys = ["%d/%d/%d/%d" % s for s in sample]
    if nmax:
        keys = keys[:nmax]
    det = YoloDetector(WEIGHTS)
    det._ensure_loaded()
    res = {}
    t0 = time.time()
    pages = sorted({int(k.split("/")[0]) for k in keys})
    for p in pages:
        pws = detect_staves(render_page(PDF[plate], p, dpi=600))
        cells = extract_measures(pws)
        local = _system_local(pws.staves)
        cell_of = {}
        for c in cells:
            k = local.get(c.staff_index)
            if k:
                cell_of[(k[0], k[1], c.measure_index)] = c
        for key in [k for k in keys if int(k.split("/")[0]) == p]:
            _, s, st, ci = [int(v) for v in key.split("/")]
            c = cell_of.get((s, st, ci))
            if c is None:
                res[key] = dict(error="no cell")
                continue
            os.environ.pop("OMR_DETECTOR_VIEWS_PARTS", None)
            t = time.perf_counter()
            kw = dict(imgsz=imgsz_for_cell(c) + 32) if perturb else {}
            prod = det.detect(c, conf_threshold=0.25, **kw)
            t_prod = time.perf_counter() - t
            prod_pg = [[d.smufl_name, round(d.confidence, 4)] + page_box(c, d) for d in prod]
            # control 1: the record's detector boxes for this cell
            rg = [(g["cls"], g["conf"], g["bbox"]) for g in rec.get(key, {}).get("glyphs", []) if g.get("reader") == "detector"]
            match = 0
            for cls, conf, bb in rg:
                if any(q[0] == cls and abs(q[1] - conf) < 0.01 and iou(q[2:6], bb) > 0.8 for q in prod_pg):
                    match += 1
            row = dict(page=p, prod=prod_pg, rec_n=len(rg), rec_match=match, t_prod=t_prod,
                       cell=[float(v) for v in c.bbox_page_px], variants={})
            for name, env in VARIANTS.items():
                for k, v in env.items():
                    os.environ[k] = v
                t = time.perf_counter()
                o = DV.views_for_cell(det, c, prod)
                dt = time.perf_counter() - t
                os.environ.pop("OMR_DETECTOR_VIEWS_PARTS", None)
                if o is None:
                    row["variants"][name] = dict(error="none", t=dt)
                    continue

                def pack(lst):
                    return [dict(cls=x["det"].smufl_name, conf=round(x["conf"], 4), fam=x["family"], view=x["view"], phases=x["phases"],
                                 phase_confs=x["phase_confs"], box=page_box(c, x["det"]), why=x.get("why")) for x in lst]
                row["variants"][name] = dict(t=dt, calls=o["calls"], kept=pack(o["kept"]), refused=pack(o["refused"]))
            res[key] = row
        print("page", p, "done", round(time.time() - t0), "s", flush=True)
    json.dump(res, open(out, "w"), default=float)
    print("wrote", out, len(res), flush=True)


if __name__ == "__main__":
    main()
