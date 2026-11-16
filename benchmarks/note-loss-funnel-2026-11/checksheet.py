"""ROADMAP 2.311 -- print-check sheets for OUR OWN look (rule 7): crops of the un-erased page, one thin box each, numbered.

    from checksheet import sheet
    sheet([dict(plate=, page=, box=[x0,y0,x1,y1], label=...), ...], out_png, width=360, cols=3, pad_units=(5, 4))

Not a tile set for Sean (labels are drawn under each crop); a check that a bucket holds what its name says.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged.lane_report import LIB, PLATES

_CACHE: dict = {}


def page_image(plate: str, pg: int) -> Image.Image:
    if (plate, pg) not in _CACHE:
        if len(_CACHE) > 2:
            _CACHE.clear()
        _CACHE[(plate, pg)] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    return _CACHE[(plate, pg)]


def sheet(items: list, out_png: str, width: int = 360, cols: int = 3, pad_units=(5, 4), color=(255, 140, 0)) -> None:
    tiles = []
    for it in sorted(items, key=lambda i: (i["plate"], i["page"])):
        im = page_image(it["plate"], it["page"])
        u = PLATES[it["plate"]]["unit"]
        b = it["box"]
        px, py = pad_units
        x0, y0 = max(0, int(b[0] - px * u)), max(0, int(b[1] - py * u))
        x1, y1 = int(b[2] + px * u), int(b[3] + py * u)
        crop = im.crop((x0, y0, x1, y1)).copy()
        ImageDraw.Draw(crop).rectangle([b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0], outline=color, width=max(2, int(u / 10)))
        s = width / crop.width
        crop = crop.resize((width, max(1, int(crop.height * s))))
        tiles.append((it, crop))
    h = max(t.height for _, t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (width + 8) + 8, rows * (h + 40) + 8), (255, 255, 255))
    d = ImageDraw.Draw(sh)
    for n, (it, t) in enumerate(tiles):
        x, y = 8 + (n % cols) * (width + 8), 8 + (n // cols) * (h + 40)
        sh.paste(t, (x, y))
        d.text((x, y + t.height + 2), ("%d " % (n + 1)) + str(it.get("label", ""))[:60], fill=(0, 0, 0))
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    sh.save(out_png)
