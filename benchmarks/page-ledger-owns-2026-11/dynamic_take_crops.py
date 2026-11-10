"""2.284 r9: crops of the in-staff dynamic claims -- the ink the claim OWNS in the page ledger tinted orange, a thin box at the claim's extent, nothing else.

    usage: dynamic_take_crops.py plate probe.json OUTDIR [--n 8] [--must PAGE:x0,y0] [--wordbox]

One staff each (the crop spans the claim's staff lines and a margin, 10 spaces either side of the claim). The owned ink is the ledger's: the ink of the strokes
the stroke_owner verdict gives the claim (`owned_boxes` of the probe), staff-line runs left grey. `--wordbox` also draws the DETECTOR's wide letter box
(`word_box`, what the r2 tiles drew) as a thin blue box, for the diagnostic copy only.
"""
import argparse
import json
import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dynamic_take_probe as P  # noqa: E402
from tools.omr.staged import claim_readout as CR  # noqa: E402


def staff_span(rows, system_sub, y):
    best = None
    for o in rows["observations"]:
        if o["quantity"] == "staff_lines" and isinstance(o["value"], list) and len(o["value"]) >= 5:
            top, bot = float(o["value"][0]), float(o["value"][-1])
            d = 0 if top <= y <= bot else min(abs(y - top), abs(y - bot))
            if best is None or d < best[0]:
                best = (d, top, bot)
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plate")
    ap.add_argument("probe")
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--src", required=True)
    ap.add_argument("--must", action="append", default=[])
    ap.add_argument("--wordbox", action="store_true")
    a = ap.parse_args()
    d = json.load(open(a.probe))
    items = []
    for pg, v in d["pages"].items():
        for r in v["claims"]:
            items.append((int(pg), r))
    must = []
    for m in a.must:
        pg, xy = m.split(":")
        x, y = (float(t) for t in xy.split(","))
        for it in items:
            if it[0] == int(pg) and it[1]["box"][0] <= x <= it[1]["box"][2] + 1 and it[1]["box"][1] <= y <= it[1]["box"][3] + 1:
                must.append(it)
    rest = sorted((it for it in items if it not in must), key=lambda it: -it[1]["owned_px"])
    pick = (must + rest)[:a.n]
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cache, key = {}, []
    for k, (pg, r) in enumerate(pick, 1):
        if pg not in cache:
            from tools.omr.preprocessing import render_page
            from tools.omr.staged import lane_report as LR
            pi = render_page(str(LR.LIB / LR.PLATES[a.plate]["pdf"]), pg, dpi=600)
            rows = CR.read_rows(pathlib.Path(a.src), [pg])
            cache[pg] = (pi.rgb, pi.binary, rows)
        rgb, binary, rows = cache[pg]
        sp = r["sp"]
        bx = r["box"]
        wb = None
        if a.wordbox:
            for o in rows["observations"]:
                if o["id"] == r["id"]:
                    wb = (o.get("detail") or {}).get("word_box")
        ext = [bx] + ([wb] if wb else [])
        x0 = int(min(e[0] for e in ext) - 10 * sp)
        x1 = int(max(e[2] for e in ext) + 10 * sp)
        top, bot = staff_span(rows, None, (bx[1] + bx[3]) / 2)
        y0 = int(min(top, min(e[1] for e in ext)) - 4 * sp)
        y1 = int(max(bot, max(e[3] for e in ext)) + 4 * sp)
        H, W = binary.shape
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        crop = rgb[y0:y1, x0:x1].copy()
        if crop.ndim == 2:
            crop = cv2.cvtColor(crop, cv2.COLOR_GRAY2RGB)
        ink = binary == 0
        mask = np.zeros_like(ink)
        for b in r["owned_boxes"]:
            bx0, by0, bx1, by1 = max(0, int(b[0]) - 1), max(0, int(b[1]) - 1), min(W, int(b[2]) + 2), min(H, int(b[3]) + 2)
            mask[by0:by1, bx0:bx1] = True
        ink_ns = P.ink_without_staff(binary, sp)
        own = (mask & ink_ns)[y0:y1, x0:x1]
        crop[own] = (255, 140, 0)
        cv2.rectangle(crop, (int(bx[0]) - x0, int(bx[1]) - y0), (int(bx[2]) - x0, int(bx[3]) - y0), (255, 140, 0), 1)
        if wb:
            cv2.rectangle(crop, (int(wb[0]) - x0, int(wb[1]) - y0), (int(wb[2]) - x0, int(wb[3]) - y0), (0, 90, 255), 1)
        name = "claim_%02d.png" % k
        cv2.imwrite(str(out / name), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        key.append(dict(file=name, page=pg, plate=a.plate, claim_box=bx, text=r["text"] or r["letter"], source=r["source"], owned_px=r["owned_px"],
                        taken_px=r["taken_px"], inside_px=r["inside_px"], crop_origin=[x0, y0], word_box=wb))
    (out / "key.json").write_text(json.dumps(key, indent=1))
    print(len(key), "crops ->", out)


if __name__ == "__main__":
    main()
