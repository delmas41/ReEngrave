"""arcs-r2: a look crop of page-ink runs against the print, from a replay's `<plate>.<arm>.extra.json` and the slice's rows.

    python3 crops_r2.py PLATE SLICEDIR EXTRA.json OUTDIR PAGE:RUN[,RUN...] [...]
The run's own ink trace (orange), the head each end bound (green start / magenta stop), the bar edges of the cell row (thin grey, `cell_box`), nothing else.
`--cells` is always on: a barline between an end and a head is the thing to look at.
"""
import json
import os
import pathlib
import sys

import cv2
import fitz
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.omr.staged import lane_report as L  # noqa: E402


def load(plate, slicedir, pages):
    sd = pathlib.Path(slicedir) / plate
    cells, heads, runs = {}, {}, {}
    for line in open(sd / "observations.jsonl"):
        o = json.loads(line)
        q, s = o["quantity"], o["subject"]
        if q == "cell_box" and int(s.split("/")[1]) in pages:
            cells[s] = o["value"]
        elif q == "glyph_box" and int(s.split("/")[1]) in pages and (o.get("detail") or {}).get("category") in ("notehead", "rest", "stem"):
            heads[s] = o["detail"]["bbox_page_px"]
        elif q == "page_arc" and o["value"] == "run" and int(s.split("/")[1]) in pages:
            runs[(int(s.split("/")[1]), o["detail"]["ordinal"])] = o["detail"]
    return cells, heads, runs


def crop(plate, slicedir, extra, outd, specs, label=""):
    pages = {int(s.split(":")[0]) for s in specs}
    cells, heads, runs = load(plate, slicedir, pages)
    ex = {}
    for v in json.load(open(extra)):
        for r in v["detail"]["runs"]:
            ex[(int(v["subject"].split("/")[1]), r["ordinal"], r.get("piece"))] = r
    outd = pathlib.Path(outd)
    outd.mkdir(parents=True, exist_ok=True)
    imgs = {}
    for spec in specs:
        pg, rs = spec.split(":")
        pg = int(pg)
        if pg not in imgs:
            doc = fitz.open(str(L.LIB / L.PLATES[plate]["pdf"]))
            pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
            imgs[pg] = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        img = imgs[pg]
        for rn in rs.split(","):
            rn = int(rn)
            d = runs.get((pg, rn))
            if d is None:
                print("no run", pg, rn)
                continue
            es = [v for k, v in ex.items() if k[0] == pg and k[1] == rn]
            pts = np.array(d["points"], float)
            sp = float(d["space_page_px"])
            bound = []
            for e in es:
                for side, col in (("left", (0, 160, 0)), ("right", (200, 0, 200))):
                    b = e.get(side) or {}
                    if b.get("head") in heads:
                        bound.append((heads[b["head"]], col))
            xs = list(pts[:, 0]) + [b[0][0] for b in bound] + [b[0][2] for b in bound]
            ys = list(pts[:, 1]) + [b[0][1] for b in bound] + [b[0][3] for b in bound]
            PAD = float(os.environ.get('CROP_PAD', 5))
            X0, X1 = int(max(0, min(xs) - PAD * sp)), int(min(img.shape[1], max(xs) + PAD * sp))
            Y0, Y1 = int(max(0, min(ys) - 4 * sp)), int(min(img.shape[0], max(ys) + 4 * sp))
            im = cv2.cvtColor(img[Y0:Y1, X0:X1].copy(), cv2.COLOR_GRAY2BGR)
            for c in ([] if os.environ.get('CROP_RAW') else cells.values()):
                for x in (c[0], c[2]):
                    if X0 <= x <= X1 and c[1] < Y1 and c[3] > Y0:
                        cv2.line(im, (int(x - X0), 0), (int(x - X0), im.shape[0]), (160, 160, 160), 1)
            RAW = bool(os.environ.get('CROP_RAW'))
            if not RAW:
              cv2.polylines(im, [np.array([(p[0] - X0, p[1] - Y0) for p in pts], np.int32)], False, (0, 140, 255), 2)
            for b, col in ([] if RAW else bound):
                cv2.rectangle(im, (int(b[0] - X0), int(b[1] - Y0)), (int(b[2] - X0), int(b[3] - Y0)), col, 3)
            s = min(float(os.environ.get('CROP_SCALE', 0.8)), 1400.0 / im.shape[1])
            im = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            e0 = es[0] if es else {}
            cv2.rectangle(im, (0, 0), (im.shape[1], 16), (255, 255, 255), -1)
            cv2.putText(im, "%s%s p%d run%d %s %s" % (label, plate, pg, rn, e0.get("status"), e0.get("kind") or e0.get("why")), (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
            cv2.imwrite(str(outd / ("%s%s-p%d-run%d.png" % (label, plate, pg, rn))), im)
    print("crops ->", outd)


if __name__ == "__main__":
    crop(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
