"""PAGE-INK ARCS feasibility (measure only): contact sheets for the agent's OWN look (not tiles for Sean -- things are drawn on them).

    python3 sheet.py PLATE PAGE WORKDIR VERSION WHAT    (WHAT: missed | fakes | lone)

missed: Brahms p0 printed arcs the ink-first runs missed or got short (hand boxes blue, runs green, detector curves orange).
fakes:  ink-first runs on no hand arc (Brahms p0), or (lone) runs no kept detector curve overlaps (Litolff p16) -- run green, numbered.
"""
import json
import pathlib
import sys

import cv2
import numpy as np


def main():
    plate, page, wd, ver, what = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4], sys.argv[5]
    stem = "%s-p%d" % (plate, page)
    raw = cv2.cvtColor(cv2.imread(str(wd / (stem + ".raw.png")), 0), cv2.COLOR_GRAY2BGR)
    R = json.load(open(wd / ("%s.%s.runs.json" % (stem, ver))))
    S = json.load(open(wd / ("%s.%s.score.json" % (stem, ver))))
    sp = R["sp"]
    runs = {r["id"]: r for r in R["runs"]}
    tiles = []
    if what == "missed":
        items = [a for a in S["per_arc"] if a["ink"] in ("missed", "short")]
        for a in items:
            x0, y0, x1, y1 = a["box"]
            tiles.append(((x0, y0, x1, y1), "%s %s det:%s" % (a["ink"], ",".join(a["ids"]), a["det"]), [a["box"]]))
    elif what == "detnorun":
        for d in S["det_curves_no_run"]:
            tiles.append((d["box"], "det %s %s best%.2f" % (d["id"], d["fate"], d["best"]), [d["box"]]))
    else:
        key = {"fakes": "ink_fakes", "cfakes": "CLIPPED_ink_unmatched"}.get(what, "ink_runs_no_det_curve")
        for i in S[key]:
            r = runs[i]
            tiles.append((r["box"], "run %d w%.1f sag%.2f th%.2f" % (i, r["width_sp"], r["sagitta_sp"], r["thick_sp"]), []))
    out = []
    for (x0, y0, x1, y1), label, hboxes in tiles:
        m = 3 * sp
        X0, Y0, X1, Y1 = int(max(0, x0 - m)), int(max(0, y0 - m)), int(min(raw.shape[1], x1 + m)), int(min(raw.shape[0], y1 + m))
        img = raw[Y0:Y1, X0:X1].copy()
        for hb in hboxes:
            cv2.rectangle(img, (int(hb[0] - X0), int(hb[1] - Y0)), (int(hb[2] - X0), int(hb[3] - Y0)), (255, 120, 0), 2)
        for r in R["runs"]:
            p = np.array(r["pts"]) - [X0, Y0]
            if (p[:, 0] >= 0).any() and (p[:, 0] < X1 - X0).any():
                cv2.polylines(img, [p.astype(np.int32).reshape(-1, 1, 2)], False, (0, 170, 0), 2)
        s = 260.0 / img.shape[0]
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        if img.shape[1] > 900:
            img = cv2.resize(img, (900, int(img.shape[0] * 900 / img.shape[1])), interpolation=cv2.INTER_AREA)
        canvas = np.full((300, 900, 3), 255, np.uint8)
        canvas[40:40 + img.shape[0], :img.shape[1]] = img
        cv2.putText(canvas, label[:80], (4, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
        out.append(canvas)
    for k in range(0, len(out), 8):
        page_img = np.vstack(out[k:k + 8])
        cv2.imwrite(str(wd / ("%s.%s.%s-%02d.png" % (stem, ver, what, k // 8))), page_img)
    print(len(out), "tiles")


if __name__ == "__main__":
    main()
