"""Crop the heads the INK says the grid misplaces, and draw both answers on
the page so a human can adjudicate one at a time.

⚠️ THE SCALE IS VERIFIED, NOT ASSUMED. The record's `staff_lines` for
`staff/1/0/0` read 1148/1163/1179/1195/1210; a 600-dpi render of pdf page 1
has its dark rows centred at 1147.5/1163/1179/1194/1210. Page pixels ARE the
600-dpi raster, checked before a single crop was cut.

Each crop carries, drawn on the image:
  * CYAN  ticks -- where the GRID says the staff positions are, extrapolated
    outward at the staff's own average line gap. This is what the pipeline
    reads a pitch against.
  * a RED box -- the notehead as detected.
  * a GREEN line -- the position the counted ledger rungs put it at.
If the printed rungs sit on the cyan ticks, the grid is right and my
measurement is wrong. If they drift off them, the grid is extrapolating at a
pitch the plate does not print.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from recordstream import stream_array  # noqa: E402

DPI = 600


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--heads", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--only-wrong", action="store_true")
    a = ap.parse_args()

    lines_of: dict[str, list[float]] = {}
    for o in stream_array(a.record, "observations"):
        if o.get("quantity") == "staff_lines" and isinstance(o.get("value"), list):
            lines_of[o["subject"]] = [float(x) for x in o["value"]]
    print(f"staves with page-pixel lines: {len(lines_of)}")

    rows = json.load(open(a.heads))
    sel = [r for r in rows if not r["relocated"] and r.get("page_box")]
    if a.only_wrong:
        sel = [r for r in sel if r["wrong"]]
    sel.sort(key=lambda r: -abs(r["error"]))
    sel = sel[:a.limit]
    if not sel:
        print("DEAD: nothing to crop", file=sys.stderr)
        return 2
    print(f"cropping {len(sel)} heads")

    doc = fitz.open(a.pdf)
    pages: dict[int, Image.Image] = {}
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    made = []
    for r in sel:
        p = r["subject"].split("/")
        page_i, sys_i, staff_i = int(p[1]), int(p[2]), int(p[3])
        st = f"staff/{page_i}/{sys_i}/{staff_i}"
        lines = lines_of.get(st)
        if lines is None or len(lines) < 5:
            print(f"  skip {r['subject']}: no staff lines")
            continue
        if page_i not in pages:
            pm = doc[page_i].get_pixmap(dpi=DPI)
            pages[page_i] = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
        img = pages[page_i]
        lines = sorted(lines)
        half = statistics.fmean(
            [lines[i + 1] - lines[i] for i in range(4)]) / 2.0
        top = lines[0]
        x0, y0, x1, y1 = r["page_box"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # a generous window: the whole staff plus the head's own reach
        wy0 = min(lines[0], cy) - 6 * half
        wy1 = max(lines[4], cy) + 6 * half
        wx0, wx1 = cx - 26 * half, cx + 26 * half
        box = (int(max(0, wx0)), int(max(0, wy0)),
               int(min(img.width, wx1)), int(min(img.height, wy1)))
        crop = img.crop(box).convert("RGB")
        scale = 4
        crop = crop.resize((crop.width * scale, crop.height * scale),
                           Image.LANCZOS)
        d = ImageDraw.Draw(crop)

        def X(v):
            return (v - box[0]) * scale

        def Y(v):
            return (v - box[1]) * scale

        # cyan ticks: the GRID's extrapolated staff positions
        pos = -14
        while pos <= 22:
            y = top + pos * half
            if box[1] <= y <= box[3]:
                inside = 0 <= pos <= 8
                col = (0, 120, 200) if inside else (0, 200, 220)
                w = 3 if pos % 2 == 0 else 1
                d.line([(X(cx) - 22 * half * scale, Y(y)),
                        (X(cx) - 15 * half * scale, Y(y))], fill=col, width=w)
                if pos % 2 == 0 and not inside:
                    d.text((X(cx) - 25 * half * scale, Y(y) - 7),
                           f"{pos}", fill=col)
            pos += 1
        # red: the detected notehead
        d.rectangle([X(x0), Y(y0), X(x1), Y(y1)], outline=(220, 0, 0), width=2)
        # green: where the counted rungs put it
        yt = top + r["true_pos"] * half
        d.line([(X(cx) - 4 * half * scale, Y(yt)),
                (X(cx) + 4 * half * scale, Y(yt))], fill=(0, 170, 0), width=2)
        d.text((6, 6),
               f"{r['subject']}  {r['side']} {r['kind']} rung {r['m']}   "
               f"grid reads {r['read_pos']:+.2f} -> {r['rounded']:+d}   "
               f"ink says {r['true_pos']:+.0f}   "
               f"{'WRONG' if r['wrong'] else 'right'}",
               fill=(200, 0, 0))
        name = r["subject"].replace("/", "_") + ".png"
        crop.save(outdir / name)
        made.append(name)
        print(f"  {name}  read {r['read_pos']:+.2f} ink {r['true_pos']:+.0f} "
              f"{'WRONG' if r['wrong'] else 'right'}")
    print(f"\nwrote {len(made)} crops to {outdir}")
    return 0 if made else 2


if __name__ == "__main__":
    raise SystemExit(main())
