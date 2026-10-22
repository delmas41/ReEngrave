"""Draw the DETECTED staff band of every vetoed staff on the printed page.

The strip sheet pads each band by a staff height so the clef is legible, which
means a neighbour bleeds into every crop — good enough to read a clef, not good
enough to *attribute* one. This draws the band itself on the page, boxed and
indexed, so the adjudication reads a clef that is unambiguously inside the box
the detector drew.

One image per (page, string block).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
       "symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
       "imslp984073.pdf")
DPI = 600

#: (page_index, first detected staff index of the block, last) — the string
#: block of every system that holds a veto, plus its unvetoed bass neighbour.
BLOCKS = [
    (56, 6, 9), (56, 15, 18),
    (57, 5, 8), (57, 20, 23),
    (63, 2, 5), (63, 9, 12), (63, 19, 22),
    (86, 12, 15),
]


def main() -> None:
    geom = json.loads((ROOT / "out" / "staffgeom600.json").read_text())
    doc = fitz.open(PDF)
    cache: dict[int, Image.Image] = {}
    for page_index, lo, hi in BLOCKS:
        if page_index not in cache:
            pix = doc[page_index].get_pixmap(dpi=DPI)
            cache[page_index] = Image.frombytes(
                "RGB", (pix.width, pix.height), pix.samples)
        img = cache[page_index].copy()
        info = geom[str(page_index)]
        band = [s for s in info["staves"] if lo <= s["idx"] <= hi]
        top = int(min(s["y0"] for s in band)) - 90
        bot = int(max(s["y1"] for s in band)) + 90
        crop = img.crop((0, max(0, top), int(info["w"] * 0.40), bot))
        draw = ImageDraw.Draw(crop)
        for s in band:
            draw.rectangle([4, int(s["y0"]) - top, 150, int(s["y1"]) - top],
                           outline=(255, 0, 0), width=7)
            draw.text((170, int(s["y0"]) - top), str(s["idx"]), fill=(255, 0, 0))
        dest = ROOT / "out" / f"page{page_index:03d}_s{lo}-{hi}.png"
        crop.resize((crop.width // 2, crop.height // 2)).save(dest)
        print("wrote", dest)


if __name__ == "__main__":
    main()
