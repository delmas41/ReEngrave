"""2.305 r10 -- why the page-ink reader (`page_arcs.read_runs`, GATHER) files no run over a window: the runs and the REJECTED tracks (with the reason
word) that lie in it. Canvas from page-ink-2026-11/canvas.py; boxes and claimed areas from a gathered record (as `gather_page_arcs` takes them).

    python3 dbg_runs.py CANVAS_DIR PLATE PAGE RECORD.json X0 Y0 X1 Y1 [X0 Y0 X1 Y1 ...]
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import cv2  # noqa: E402
import numpy as np  # noqa: E402

from tools.omr.staged import page_arcs as m  # noqa: E402
from tools.omr.staged.record_io import load_record  # noqa: E402


def load(cdir, plate, page, rec_path):
    stem = os.path.join(cdir, "%s-p%d" % (plate, page))
    canvas = cv2.imread(stem + ".canvas.png", cv2.IMREAD_GRAYSCALE)
    raw = cv2.imread(stem + ".raw.png", cv2.IMREAD_GRAYSCALE)
    pj = json.load(open(stem + ".page.json"))
    rec = load_record(rec_path)["record"]
    rows = []
    pre = "glyph/%d/" % page
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box" and o["subject"].startswith(pre):
            rows.append(("glyph_box", o["subject"], o.get("value"), o.get("detail") or {}))
        elif o["quantity"] == "claimed_area" and (o["subject"].startswith("staff/%d/" % page) or o["subject"].startswith("page/%d" % page)
                                                  or o["subject"].startswith(pre)):
            rows.append(("claimed_area", "", o.get("value"), o.get("detail") or {}))
    boxes, areas, arc_boxes = m.inputs_from_rows(rows)
    line_ys = [y for s in pj["staves"] for y in s["lines"]]
    return canvas, raw, float(pj["sp"]), line_ys, boxes, areas, arc_boxes


def main():
    cdir, plate, page, rec_path = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    wins = [list(map(float, sys.argv[i:i + 4])) for i in range(5, len(sys.argv), 4)]
    canvas, raw, sp, line_ys, boxes, areas, arc_boxes = load(cdir, plate, page, rec_path)
    res = m.read_runs(canvas, sp, line_ys, boxes, areas, keep_rejected=True, raw=(raw if raw is not None else None), arc_boxes=arc_boxes)
    print("sp", sp, "scale", res["scale"], "runs", len(res["runs"]))
    for w in wins:
        x0, y0, x1, y1 = w
        print("WINDOW", w)
        for q in res.get("rejected_tracks") or ():
            P = np.array(q["pts"])
            if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].min() > y1 or P[:, 1].max() < y0:
                continue
            print("   rejected %-22s x %.0f-%.0f y %.0f..%.0f n %d" % (q["why"], P[:, 0].min(), P[:, 0].max(), P[:, 1].min(), P[:, 1].max(), len(P)))
        for r in res["runs"]:
            if r["box"][2] < x0 or r["box"][0] > x1 or r["box"][3] < y0 or r["box"][1] > y1:
                continue
            print("   run %s %s width %.2f sag %.2f" % (r["id"], [round(v) for v in r["box"]], r["width_sp"], r["sagitta_sp"]))


if __name__ == "__main__":
    main()
