"""2.274 step 2 r2: crops of witnessed runs for MY look (development aid; NOT tiles for Sean).

    python3 look.py WORKDIR SLICEDIR OUTDIR PLATE PAGE ORD[,ORD...]

One crop per run, cut from the page at 600 dpi: the run's ink trace (thin orange, dots at the two ends of the ink = `core_ends`), every notehead box of the staff (thin grey), the heads
the binder bound (green = start, magenta = stop; the file's written kind in the header), and the OFF arcs over the run (blue lines from head to head). Nothing is drawn for Sean here.
"""
import json
import pathlib
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[4]))
sys.path.insert(0, str(HERE.parents[5]))

import arcs as A  # noqa: E402
import measure_first as M  # noqa: E402
from tools.omr.staged import lane_report as L  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402

GREEN, MAG, GREY, ORANGE, BLUE = (0, 160, 0), (200, 0, 200), (150, 150, 150), (0, 140, 255), (230, 120, 0)


def heads_of(slicedir, plate, page):
    out = {}
    with open(pathlib.Path(slicedir) / plate / "observations.jsonl") as fh:
        for line in fh:
            if '"glyph_box"' not in line:
                continue
            o = json.loads(line)
            if o["quantity"] != "glyph_box" or L.page_of(o["subject"]) != page:
                continue
            d = o.get("detail") or {}
            if d.get("category") == "notehead" and d.get("bbox_page_px"):
                out[o["subject"]] = [float(v) for v in d["bbox_page_px"]]
    return out


def crop_run(im, plate, page, r, row, heads, boxes, off_over, out, label):
    sp = L.PLATES[plate]["unit"]
    pts = np.array(row["points"], float)
    st = tuple(r["staff"])
    sh = {k: b for k, b in heads.items() if A.staff_of(k) and A.staff_of(k)[1:] == st}
    xs0, xs1 = pts[:, 0].min() - 3 * sp, pts[:, 0].max() + 3 * sp
    ys0, ys1 = pts[:, 1].min() - 6 * sp, pts[:, 1].max() + 6 * sp
    for k in (r.get("start"), r.get("stop")):
        if k and k in boxes:
            b = boxes[k]["box"]
            xs0, xs1 = min(xs0, b[0] - sp), max(xs1, b[2] + sp)
            ys0, ys1 = min(ys0, b[1] - 3 * sp), max(ys1, b[3] + 3 * sp)
    x0, x1 = int(max(0, xs0)), int(min(im.shape[1], xs1))
    y0, y1 = int(max(0, ys0)), int(min(im.shape[0], ys1))
    crop = im[y0:y1, x0:x1].copy()
    sc = min(2.5, 1500.0 / max(1, x1 - x0))
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)

    def P(x, y):
        return int((x - x0) * sc), int((y - y0) * sc)

    for k, b in sh.items():
        if b[2] < x0 or b[0] > x1:
            continue
        cv2.rectangle(crop, P(b[0], b[1]), P(b[2], b[3]), GREY, 1)
    for k, c in ((r.get("start"), GREEN), (r.get("stop"), MAG)):
        if k and k in boxes:
            b = boxes[k]["box"]
            cv2.rectangle(crop, P(b[0] - 2, b[1] - 2), P(b[2] + 2, b[3] + 2), c, 2)
    for a in off_over:
        if a["start"] in boxes and a["stop"] in boxes:
            ba, bz = boxes[a["start"]]["box"], boxes[a["stop"]]["box"]
            ya = ba[1] - 0.8 * sp if row["sagitta_spaces"] < 0 else ba[3] + 0.8 * sp
            cv2.line(crop, P((ba[0] + ba[2]) / 2, ya), P((bz[0] + bz[2]) / 2, ya), BLUE, 1)
            cv2.putText(crop, a["kind"][0], P((ba[0] + ba[2]) / 2, ya - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 1)
    cv2.polylines(crop, [np.array([P(x, y) for x, y in pts], np.int32)], False, ORANGE, 1, cv2.LINE_AA)
    ce = row.get("core_ends")
    if ce:
        for (x, y), c in zip(ce, (GREEN, MAG)):
            cv2.circle(crop, P(x, y), 6, c, -1)
    pad = np.full((26, crop.shape[1], 3), 255, np.uint8)
    cv2.putText(pad, label, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1)
    cv2.imwrite(str(out), np.vstack([pad, crop]))


def main():
    workdir, slicedir, outdir, plate, page, ords = sys.argv[1:7]
    page = int(page)
    ords = [int(x) for x in ords.split(",")]
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    off, on, extra, boxes, runs = M.load(workdir, slicedir, plate, [page])
    recs = {r["ordinal"]: r for r in A.per_run(extra, off, boxes, runs)}
    heads = heads_of(slicedir, plate, page)
    im = cv2.cvtColor(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), page, dpi=600).rgb, cv2.COLOR_RGB2BGR)
    for o in ords:
        r = recs.get(o)
        if r is None:
            print("no record for run", o)
            continue
        row = runs[(page, o)]
        label = "%s p%d run %d  %s  start=%s stop=%s  off=%s why=%s closest=%s" % (plate, page, o, r["status"] + "/" + str(r.get("kind")), (r.get("start") or "-")[-9:],
                                                                                   (r.get("stop") or "-")[-9:], r.get("off"), r.get("why"), r.get("closest"))
        crop_run(im, plate, page, r, row, heads, boxes, r["off_overlap"], out / ("%s-p%d-run%03d.png" % (plate, page, o)), label)
        print("wrote", o)


if __name__ == "__main__":
    main()
