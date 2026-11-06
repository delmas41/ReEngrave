"""PAGE-INK ARCS feasibility: 8 crops of ink-first runs, ONE staff wide in y, the run's whole arc boxed (thin orange), nothing else drawn.

    python3 crops.py WORKDIR OUTDIR brahms:0:21,brahms:0:43,...
"""
import json
import pathlib
import sys

import cv2


def main():
    wd, out, spec = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    key = []
    for n, item in enumerate(spec.split(","), 1):
        plate, page, rid = item.split(":")
        stem = "%s-p%s" % (plate, page)
        raw = cv2.cvtColor(cv2.imread(str(wd / (stem + ".raw.png")), 0), cv2.COLOR_GRAY2BGR)
        meta = json.load(open(wd / (stem + ".page.json")))
        R = json.load(open(wd / (stem + ".v4.runs.json")))
        sp = R["sp"]
        r = [q for q in R["runs"] if q["id"] == int(rid)][0]
        x0, y0, x1, y1 = r["box"]
        cy = (y0 + y1) / 2
        st = min(meta["staves"], key=lambda s: abs((s["lines"][0] + s["lines"][-1]) / 2 - cy))
        Y0 = int(min(y0, st["lines"][0]) - 3 * sp)
        Y1 = int(max(y1, st["lines"][-1]) + 3 * sp)
        X0, X1 = int(max(0, x0 - 4 * sp)), int(min(raw.shape[1], x1 + 4 * sp))
        img = raw[max(0, Y0):Y1, X0:X1].copy()
        pad = 0.3 * sp
        cv2.rectangle(img, (int(x0 - pad - X0), int(y0 - pad - max(0, Y0))), (int(x1 + pad - X0), int(y1 + pad - max(0, Y0))), (0, 140, 255), 2)
        f = out / ("%02d.png" % n)
        cv2.imwrite(str(f), img)
        key.append(dict(tile=n, plate=plate, page=int(page), run=int(rid), box=r["box"], width_sp=r["width_sp"]))
    json.dump(key, open(wd / "crops-key.json", "w"), indent=1)
    print(len(key), "crops ->", out)


if __name__ == "__main__":
    main()
