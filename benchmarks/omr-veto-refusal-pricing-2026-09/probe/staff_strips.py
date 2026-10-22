"""One image per page: the LEFT EDGE of every DETECTED staff, in order, indexed.

The adjudication needs to say, for a given detected staff index, what the print
actually puts there. A full-page render answers that for a page whose detected
count equals the printed count; page 86 detects 16 against 17 printed, so the
mapping has to be made staff by staff. Cropping each detected band at the same
dpi the composition ran at puts the detector's own answer beside the clef and
the margin label that settle it.

The strip is the staff band padded by one staff height above and below, from
x = 0 to 30% of the page width — enough for the margin label, the brace, the
clef and the key signature.
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
XFRAC = 0.30


def main() -> None:
    geom = json.loads((ROOT / "out" / "staffgeom600.json").read_text())
    doc = fitz.open(PDF)
    for page_key, info in geom.items():
        page_index = int(page_key)
        pix = doc[page_index].get_pixmap(dpi=DPI)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        assert (pix.height, pix.width) == (info["h"], info["w"]), (
            f"render disagrees with the probe: {pix.height}x{pix.width} "
            f"vs {info['h']}x{info['w']}")
        xw = int(info["w"] * XFRAC)
        strips = []
        for s in info["staves"]:
            h = s["y1"] - s["y0"]
            top = max(0, int(s["y0"] - h))
            bot = min(info["h"], int(s["y1"] + h))
            strips.append((s, img.crop((0, top, xw, bot))))
        gap = 24
        out_h = sum(c.height + gap for _, c in strips) + gap
        sheet = Image.new("RGB", (xw + 220, out_h), "white")
        draw = ImageDraw.Draw(sheet)
        y = gap
        for s, crop in strips:
            sheet.paste(crop, (200, y))
            draw.text((20, y + crop.height // 2),
                      f"staff {s['idx']}  sys {s['system']}",
                      fill="red")
            draw.line((200, y, 200 + xw, y), fill=(220, 220, 220))
            y += crop.height + gap
        dest = ROOT / "out" / f"page{page_index:03d}_strips.png"
        sheet.resize((sheet.width // 2, sheet.height // 2)).save(dest)
        print("wrote", dest, sheet.size)


if __name__ == "__main__":
    main()
