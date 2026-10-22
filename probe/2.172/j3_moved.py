"""2.172: for the six judged rests that got worse, where did the ink go: the subject's own ink in OFF, the ON view box(es) over it, their class and duration verdict."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = [("lit", "glyph/2/0/6/3/350000"), ("lit", "glyph/2/0/7/3/350000"), ("lit", "glyph/1/0/7/0/350000"),
         ("bra", "glyph/1/1/12/4/4"), ("bra", "glyph/1/0/4/1/350003"), ("bra", "glyph/1/0/9/6/350001")]


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


for pl in ("lit", "bra"):
    off = json.loads(open(ROOT / ("rec172/%s-off.record.json" % pl)).read())["record"]
    on = json.loads(open(ROOT / ("rec172/%s-on.record.json" % pl)).read())["record"]
    subs = [s for p, s in CASES if p == pl]
    sb = {}
    for o in off["observations"]:
        if o["subject"] in subs and o["quantity"] in ("glyph_box", "unboxed_rest_shape", "cv_unboxed_rest"):
            det = o.get("detail") or {}
            sb.setdefault(o["subject"], []).append((o["quantity"], o["value"], det.get("bbox_page_px") or det.get("bbox")))
    for s in subs:
        cell = "/".join(s.split("/")[1:5])
        print("====", pl, s, "OFF rows:", [(q, str(v)[:50], b) for q, v, b in sb.get(s, [])][:3])
        subbox = None
        for q, v, b in sb.get(s, []):
            if b:
                subbox = b
        views = []
        for o in on["observations"]:
            if o["quantity"] == "glyph_box" and o.get("reader") == "yolo_detector_view" and "/".join(o["subject"].split("/")[1:5]) == cell:
                det = o.get("detail") or {}
                views.append((o["subject"], o["value"][0], round(o.get("score") or 0, 2), det.get("bbox_page_px"), det.get("view")))
        dur = {}
        for v in on["verdicts"]:
            if v.get("quantity") == "duration" and "/".join(v.get("subject", "").split("/")[1:5]) == cell:
                dur[v["subject"]] = (v["outcome"], v.get("reason"), str(v.get("value"))[:60])
        for g, cls, sc, bb, view in views:
            ov = iou(subbox, bb) if (subbox and bb) else None
            print("   view", g.split("/")[-1], cls, sc, view, "iou-with-subject", None if ov is None else round(ov, 2), "dur:", dur.get(g))
