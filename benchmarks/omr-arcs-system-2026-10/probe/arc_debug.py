"""ROADMAP 2.166 -- iterate on the system-arc reader without a gather: one page prepared, the detector's boxes cached
to out/2.166/det_<doc>_<page>.pkl, `arcs_system.gather_system_arcs` run on a scratch Log, and an overlay drawn.

usage: arc_debug.py DOC PAGE [X0 Y0 X1 Y1 OUT.png]
  prints the summary; with a region, draws: grey = page, orange = detector arc box, green = notehead box,
  blue = traced stroke, red = ink erased from the cells (page px), magenta = stroke-only head boxes.
"""
import json
import os
import pickle
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr import acceptance as ACC  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import gather, pipeline, weight_routing  # noqa: E402
from tools.omr.staged.record import Log  # noqa: E402

DOCS = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}


def load(doc_key, page):
    man = json.load(open("benchmarks/acceptance/manifest.json"))
    doc = [d for d in man["documents"] if d["id"] == DOCS[doc_key]][0]
    pdf = str(ACC.resolve_path(doc["pdf"]))
    prepared = pipeline.prepare_pages(pdf, [page])
    pws, cells = prepared[0]
    log = Log()
    local = gather.gather_geometry(log, pws)
    cache = "out/2.166/det_%s_%d.pkl" % (doc_key, page)
    if os.path.exists(cache):
        detections = pickle.load(open(cache, "rb"))
    else:
        wpath, _, _ = weight_routing.resolve_staged_weights(pdf, [page], weights="auto", route_weights=False)
        from tools.omr.yolo_detector import YoloDetector
        gather.gather_systems(log, pws, getattr(pws, "used_bridging", True))
        gather.gather_measures(log, pws, cells, local)
        detections = gather.gather_detections(log, cells, local, detector=YoloDetector(wpath))
        pickle.dump(detections, open(cache, "wb"))
    return pws, cells, local, detections


def run(doc_key, page):
    pws, cells, local, detections = load(doc_key, page)
    os.environ[AS.ENV] = "1"
    log = Log()
    traces = []
    orig_trace = AS.trace_arc

    def spy(*a, **k):
        t = orig_trace(*a, **k)
        if t is not None:
            t = dict(t, box=a[1])
            traces.append(t)
        return t
    AS.trace_arc = spy
    try:
        summary = AS.gather_system_arcs(log, pws, cells, local, detections)
    finally:
        AS.trace_arc = orig_trace
    return pws, cells, local, detections, log, summary, traces


def draw(pws, cells, local, detections, summary, traces, region, out):
    import cv2
    x0, y0, x1, y1 = region
    page = pws.page.binary[y0:y1, x0:x1]
    if os.environ.get("DBG_COMPOSITE"):
        page = np.where(AS.composite_ink(pws.page.binary, cells)[y0:y1, x0:x1], 0, 255)
    img = cv2.cvtColor(np.where(page < 128, 90, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for c in cells:
        orig = getattr(c, "image_no_staff_with_arcs", None)
        if orig is None:
            continue
        er = (orig < 128) & ~(c.image_no_staff < 128)
        ys, xs = np.nonzero(er)
        up = float(c.upscale_factor)
        px = (c.bbox_page_px[0] + xs / up).astype(int) - x0
        py = (c.bbox_page_px[1] + ys / up).astype(int) - y0
        ok = (px >= 0) & (py >= 0) & (px < img.shape[1]) & (py < img.shape[0])
        img[py[ok], px[ok]] = (0, 0, 255)
    for t in traces:
        for x, (a, b) in t["points"].items():
            if x0 <= x < x1:
                for y in (a, b):
                    if y0 <= y < y1:
                        img[y - y0, x - x0] = (255, 120, 0)
    from tools.omr.staged import record as R
    for c in cells:
        key = local.get(c.staff_index)
        if key is None:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        for gi, d in enumerate(detections.get(sub.to_key(), ())):
            b = AS._page_box(c, d)
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi).to_key()
            if d.smufl_name in ("tie", "slur"):
                col = (0, 140, 255)
            elif str(d.smufl_name).startswith("notehead"):
                col = (255, 0, 255) if g in summary.get("stroke_only_heads", ()) else (0, 170, 0)
            else:
                continue
            cv2.rectangle(img, (int(b[0]) - x0, int(b[1]) - y0), (int(b[2]) - x0, int(b[3]) - y0), col, 1)
    cv2.imwrite(out, img)


if __name__ == "__main__":
    doc_key, page = sys.argv[1], int(sys.argv[2])
    pws, cells, local, detections, log, summary, traces = run(doc_key, page)
    print({k: v for k, v in summary.items() if k != "arcs_detail"})
    import collections
    so = collections.Counter()
    for a in summary["arcs_detail"]:
        for t in a["through_boxes"]:
            if t["stroke_only"]:
                so[t["class"]] += 1
    print("stroke-only by class", dict(so))
    if os.environ.get("DBG_SO"):
        for a in summary["arcs_detail"]:
            for t in a["through_boxes"]:
                if t["stroke_only"]:
                    print("SO", t["glyph"], t["class"], t["residual_spaces2"], "arc", a["subject"], a["x_left_page"],
                          a["x_right_page"], a["y_left_page"])
    if os.environ.get("DBG_ARCS") and len(sys.argv) > 3:
        rx0, ry0, rx1, ry1 = [int(v) for v in sys.argv[3:7]]
        for a in summary["arcs_detail"]:
            if a["x_right_page"] >= rx0 and a["x_left_page"] <= rx1 and ry0 <= a["y_left_page"] <= ry1:
                print(a["subject"], a["shape"], a["cells"], a["x_left_page"], a["x_right_page"], a["through_boxes"],
                      a["anchor_left"], a["anchor_right"], a["anchor_dy_spaces"])
    if len(sys.argv) > 3:
        region = [int(v) for v in sys.argv[3:7]]
        draw(pws, cells, local, detections, summary, traces, region, sys.argv[7])
        for t in traces:
            b = t["box"]
            if b[2] >= region[0] and b[0] <= region[2] and b[3] >= region[1] and b[1] <= region[3]:
                print("box", [int(v) for v in b], "cov", t["coverage"], "x", t["x0"], t["x1"])
