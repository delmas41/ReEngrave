"""our own look (a control, not evidence): python3 look.py N [N...] -> /tmp-like scratch out dir look/N.png
 blue = Sean's hand boxes, orange = detector arc boxes kept, grey = refused, green = step-1 page-ink run, red boxes = heads the ON file writes on the nearest written span, magenta = hand noteheads"""
import sys
import json
import cv2
import numpy as np
from load import *   # noqa
import page as PG

C = json.load(open("census3.json"))
P, HEADS = printed()
img = PG.page()
rec = record("on")
arcbox = {o["subject"]: o["detail"]["bbox_page_px"] for o in rec["observations"] if o["quantity"] == "arc_box" and o["subject"].startswith("glyph/0/")}
refused = {v["subject"]: v["value"] for v in rec["verdicts"] if v["quantity"] == "arc_is_not_an_arc"}
runs = {o["detail"]["ordinal"]: o["detail"] for o in rec["observations"] if o["quantity"] == "page_arc" and o["value"] == "run"}
gb = {o["subject"]: o["detail"]["bbox_page_px"] for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/")}
import pathlib
OUT = pathlib.Path("look")
OUT.mkdir(exist_ok=True)
for n in [int(a) for a in sys.argv[1:]]:
    c = C[n]
    p = P[n]
    x0, y0, x1, y1 = p["box"]
    pad = 110
    im, (ox, oy) = PG.crop(img, [x0 - 40, y0 - 70, x1 + 40, y1 + 90], pad=pad)
    for r in p["rects"]:
        cv2.rectangle(im, (int(r[0] - ox), int(r[1] - oy)), (int(r[2] - ox), int(r[3] - oy)), (255, 100, 0), 2)
    for k in c["boxes"]:
        b = arcbox[k]
        col = (150, 150, 150) if refused.get(k) else (0, 140, 255)
        cv2.rectangle(im, (int(b[0] - ox) + 3, int(b[1] - oy) + 3), (int(b[2] - ox) - 3, int(b[3] - oy) - 3), col, 2)
    for r in c["runs"][:3]:
        d = runs[r["ordinal"]]
        pts = np.array(d["points"]) - np.array([ox, oy])
        cv2.polylines(im, [pts.astype(np.int32).reshape(-1, 1, 2)], False, (0, 170, 0), 3)
    for h in HEADS:
        if h["staff"] == p["staff"] and x0 - 3 * SP < (h["rect"][0] + h["rect"][2]) / 2 < x1 + 3 * SP:
            r = h["rect"]
            cv2.rectangle(im, (int(r[0] - ox), int(r[1] - oy)), (int(r[2] - ox), int(r[3] - oy)), (200, 0, 200), 1)
    for key in (list(c["aud_on_span"][:2]) if c.get("aud_on_span") else [(c["near_on"] or {}).get("start"), (c["near_on"] or {}).get("stop")]):
        if key and key in gb:
            r = gb[key]
            cv2.rectangle(im, (int(r[0] - ox) - 3, int(r[1] - oy) - 3), (int(r[2] - ox) + 3, int(r[3] - oy) + 3), (0, 0, 255), 2)
    for e in c["bind"][:2]:
        for key in (e.get("start"), e.get("stop")):
            if key and key in gb:
                r = gb[key]
                cv2.rectangle(im, (int(r[0] - ox) - 6, int(r[1] - oy) - 6), (int(r[2] - ox) + 6, int(r[3] - oy) + 6), (0, 200, 200), 2)
    cv2.putText(im, "P%d %s %s ON:%s OFF:%s" % (n, c["staff"], c["kind"], c["file_on"], c["file_off"]), (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    s = min(1.0, 1500.0 / im.shape[1])
    im = cv2.resize(im, None, fx=s, fy=s)
    cv2.imwrite(str(OUT / ("P%d.png" % n)), im)
    print("wrote", OUT / ("P%d.png" % n), im.shape)
