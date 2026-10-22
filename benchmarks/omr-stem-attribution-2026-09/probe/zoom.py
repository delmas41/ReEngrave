"""Re-render named tiles from a crop manifest, larger.

⚠️ THE ZOOM IS PART OF THE INSTRUMENT -- the 2026-09-18 handoff records an
adjudicator reading two heads WRONG at tile magnification and a wider strip
correcting both. Written here because a verdict of mine (`G02`) disagreed with
the geometry the record holds for it, and one of the two had to be wrong.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from reach import collect  # noqa: E402
from omr_ledger_extrapolation_shim import stream_array  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--crops", required=True)
    ap.add_argument("--tiles", nargs="+", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--pad", type=float, default=5.0)
    ap.add_argument("--scale", type=int, default=3)
    a = ap.parse_args()

    man = json.load(open(a.crops))
    rows = [r for r in man["index"] if r["tile"] in set(a.tiles)]
    _stems, heads, _ = collect(a.record)
    pbox, lines = {}, {}
    for o in stream_array(a.record, "observations"):
        q = o.get("quantity")
        if q == "staff_lines":
            lines[o["subject"]] = o["value"]
        elif q == "glyph_box":
            d = o.get("detail") or {}
            if d.get("category") == "notehead" and d.get("bbox_page_px"):
                pbox[o["subject"]] = d["bbox_page_px"]
    aff = {}
    for c, hs in heads.items():
        pts = [(hb, pbox[s]) for s, _h, hb in hs if s in pbox]
        if not pts:
            continue
        sx = statistics.fmean([(p[2] - p[0]) / hb[2] for hb, p in pts if hb[2]])
        sy = statistics.fmean([(p[3] - p[1]) / hb[3] for hb, p in pts if hb[3]])
        ox = statistics.fmean([p[0] - hb[0] * sx for hb, p in pts])
        oy = statistics.fmean([p[1] - hb[1] * sy for hb, p in pts])
        aff[c] = (sx, sy, ox, oy)

    doc = fitz.open(a.pdf)
    cache = {}

    def page(pg):
        if pg not in cache:
            pm = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
            cache[pg] = np.frombuffer(pm.samples, dtype=np.uint8).reshape(
                pm.height, pm.width)
        return cache[pg]

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for r in sorted(rows, key=lambda r: r["tile"]):
        s = r["subject"]
        p = s.split("/")
        L = lines[f"staff/{p[1]}/{p[2]}/{p[3]}"]
        sp = statistics.fmean([L[i + 1] - L[i] for i in range(4)])
        img = page(int(p[1]))
        x0, y0, x1, y1 = pbox[s]
        sx, sy, ox, oy = aff[r["cell"]]
        bx, by, bw, bh = r["stem_box_canonical"]
        X0, Y0 = bx * sx + ox, by * sy + oy
        X1, Y1 = (bx + bw) * sx + ox, (by + bh) * sy + oy
        xa = max(0, int(min(x0, X0) - a.pad * sp))
        xb = min(img.shape[1], int(max(x1, X1) + a.pad * sp))
        ya = max(0, int(min(y0, Y0) - a.pad * sp))
        yb = min(img.shape[0], int(max(y1, Y1) + a.pad * sp))
        t = cv2.cvtColor(img[ya:yb, xa:xb], cv2.COLOR_GRAY2BGR)
        cv2.rectangle(t, (int(X0) - xa, int(Y0) - ya),
                      (int(X1) - xa, int(Y1) - ya), (255, 0, 0), 2)
        cv2.rectangle(t, (int(x0) - xa, int(y0) - ya),
                      (int(x1) - xa, int(y1) - ya), (0, 0, 255), 2)
        t = cv2.resize(t, (t.shape[1] * a.scale, t.shape[0] * a.scale),
                       interpolation=cv2.INTER_CUBIC)
        out = outdir / f"zoom-{r['tile']}.png"
        cv2.imwrite(str(out), t)
        print(f"wrote {out}  {t.shape[1]}x{t.shape[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
