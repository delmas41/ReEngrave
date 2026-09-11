"""One candidate bar, rendered LARGE with the detector's own boxes drawn on it.

⚠️ A crop at the page's own scale is 100-200 px wide here and a whole rest is
11 px tall in it; at that size a rest and a notehead are the same smudge to a
human too, which is the whole point of the question. This upscales and draws
every recorded detection, labelled, so what the detector fired on is visible
beside what the page prints.

    python3 .../zoom.py --record R --pdf P --cands C --only P1:88 --out DIR
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from crops import GATHER_DPI, detections_by_cell, locate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--cands", required=True)
    ap.add_argument("--only", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--pad", type=int, default=30)
    ap.add_argument("--no-boxes", action="store_true")
    a = ap.parse_args()

    import fitz
    from PIL import Image, ImageDraw

    result = json.load(open(a.record))
    where = locate(result)
    dets = detections_by_cell(result)
    cands = {(c["part"], c["measure"]): c for c in json.load(open(a.cands))}

    doc = fitz.open(a.pdf)
    zoom = GATHER_DPI / 72.0
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    rendered = {}
    n = 0
    for t in a.only.split(","):
        p, m = t.split(":")
        key = (p, int(m))
        c = cands[key]
        page, system, staff, cell, box = where[key]
        if page not in rendered:
            pm = doc[page].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            rendered[page] = Image.open(io.BytesIO(pm.tobytes("png"))).convert("RGB")
        img = rendered[page]
        x0, y0, x1, y1 = box
        cx0, cy0 = max(0, int(x0) - a.pad), max(0, int(y0) - a.pad)
        cx1, cy1 = min(img.width, int(x1) + a.pad), min(img.height, int(y1) + a.pad)
        sub = img.crop((cx0, cy0, cx1, cy1))
        s = a.scale
        sub = sub.resize((sub.width * s, sub.height * s), Image.LANCZOS)
        if not a.no_boxes:
            d = ImageDraw.Draw(sub)
            for cls, cf, bb, _ in dets.get((page, system, staff, cell), []):
                if not bb or len(bb) != 4:
                    continue
                r = [(bb[0] - cx0) * s, (bb[1] - cy0) * s,
                     (bb[2] - cx0) * s, (bb[3] - cy0) * s]
                col = ((220, 0, 0) if "notehead" in (cls or "")
                       else (0, 140, 0) if "rest" in (cls or "").lower()
                       else (110, 110, 240))
                d.rectangle(r, outline=col, width=2)
                d.text((r[0], max(0, r[1] - 12)),
                       f"{cls} {cf:.2f}" if cf else str(cls), fill=col)
        name = f"ZOOM-{p}-m{m}-p{page}s{system}st{staff}c{cell}.png"
        sub.save(str(outdir / name))
        print(f"{name}  exported {c['sounding']}/{c['bar_len']} "
              f"{[(e['type'], e['pitch']) for e in c['events']]}")
        n += 1
    print(f"{n} zooms -> {outdir}")


if __name__ == "__main__":
    main()
