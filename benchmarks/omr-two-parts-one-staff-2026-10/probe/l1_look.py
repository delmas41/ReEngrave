"""ROADMAP 2.182 -- crops of named bars for MY look (ours, not evidence; never sent to Sean): the bar boxed blue, glyph boxes
drawn and labelled with their index (green = upper part, orange = lower part, grey = in both) when an arm's split is given.

usage: l1_look.py DOC RECORD.json OUTDIR ARM.json BAR [BAR ...]"""
import json
import os
import sys

import cv2

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from t1_tiles import PDF  # noqa: E402

doc, rec_path, outdir, arm_path = sys.argv[1:5]
bars = sys.argv[5:]
arm = json.load(open(arm_path))
rec = load_record(rec_path)["record"]
cell_box, lines, boxes = {}, {}, {}
want = set(bars)
for o in rec["observations"]:
    s = o["subject"]
    if o["quantity"] == "cell_box" and s[5:] in want:
        cell_box[s[5:]] = o["value"]
    elif o["quantity"] == "staff_lines" and s.startswith("staff/"):
        lines.setdefault(s[6:], o["value"])
    elif o["quantity"] == "glyph_box" and s.startswith("glyph/"):
        b = "/".join(s.split("/")[1:5])
        if b in want and isinstance((o.get("detail") or {}).get("bbox_page_px"), list):
            boxes.setdefault(b, {}).setdefault(int(s.split("/")[-1]), (o["value"][0], o["detail"]["bbox_page_px"]))
del rec
os.makedirs(outdir, exist_ok=True)
page = None
for b in sorted(bars, key=lambda x: int(x.split("/")[0])):
    pg = int(b.split("/")[0])
    if page is None or page[0] != pg:
        page = (pg, cv2.cvtColor(render_page(PDF[doc], pg).rgb, cv2.COLOR_RGB2BGR))
    img = page[1]
    cb = cell_box[b]
    ys = lines.get("/".join(b.split("/")[:3]))
    sp = (ys[-1] - ys[0]) / 4.0
    X0, X1 = int(max(0, cb[0] - 2 * sp)), int(min(img.shape[1], cb[2] + 2 * sp))
    Y0, Y1 = int(max(0, ys[0] - 6 * sp)), int(min(img.shape[0], ys[-1] + 6 * sp))
    plain = img[Y0:Y1, X0:X1].copy()
    ann = plain.copy()
    tp = (arm.get("two_parts") or {}).get(b)
    up, lo = (set(tp["voices"][0]), set(tp["voices"][1])) if tp else (set(), set())
    for gi, (cls, bb) in sorted(boxes.get(b, {}).items()):
        col = (128, 128, 128) if (gi in up and gi in lo) else (0, 160, 0) if gi in up else (0, 140, 255) if gi in lo else (200, 0, 200)
        if not (gi in up or gi in lo):
            continue
        cv2.rectangle(ann, (int(bb[0] - X0), int(bb[1] - Y0)), (int(bb[2] - X0), int(bb[3] - Y0)), col, 2)
        cv2.putText(ann, "%d%s" % (gi, cls[4:7]), (int(bb[0] - X0), int(bb[1] - Y0) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
    both = cv2.vconcat([plain, ann])
    k = 900.0 / both.shape[1]
    both = cv2.resize(both, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(outdir, b.replace("/", "_") + ".png"), both)
print("wrote", len(bars))
