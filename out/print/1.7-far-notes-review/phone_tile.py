"""Drawing helpers for the phone-sized review tiles (ROADMAP 1.7 far-note review, Sean 2026-10-10).

Not product code: a diagnostic image maker. Everything is drawn at the FINAL (scaled-up) resolution, after the
print crop has been resized, so line weights are in phone pixels, not page pixels.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REGULAR = "/Library/Fonts/Arial.ttf"
ORANGE = (240, 120, 0)
GREY = (105, 105, 115)
RED = (215, 0, 0)
GREEN = (0, 150, 40)
BLUE = (30, 90, 220)
INK = (20, 20, 20)
WIDTH = 1000          # phone-friendly: 800-1000 px wide
MAX_CROP_H = 1750     # a tall pair of staves is scaled down, never cut


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REGULAR, size)


def text_w(draw: ImageDraw.ImageDraw, s: str, f) -> float:
    return draw.textlength(s, font=f)


def crop_scaled(img: np.ndarray, box: Tuple[float, float, float, float], width: int = WIDTH,
                max_h: int = MAX_CROP_H) -> Tuple[Image.Image, float, Tuple[int, int]]:
    """Crop ``box`` (page px) out of the page and scale it to ``width`` (or smaller if it would be taller
    than ``max_h``). Returns (image, scale, (x0, y0) of the crop in page px)."""
    h, w = img.shape[:2]
    x0, y0 = max(0, int(round(box[0]))), max(0, int(round(box[1])))
    x1, y1 = min(w, int(round(box[2]))), min(h, int(round(box[3])))
    crop = Image.fromarray(img[y0:y1, x0:x1]).convert("RGB")
    scale = min(width / crop.width, max_h / crop.height)
    return crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))), Image.LANCZOS), scale, (x0, y0)


def fit_runs(draw: ImageDraw.ImageDraw, runs: Sequence[Tuple[str, Tuple[int, int, int]]], max_w: int,
             sizes=(34, 32, 30, 28, 26, 24, 22), bold: bool = True):
    """The biggest font in ``sizes`` at which the coloured runs fit on one line of ``max_w``."""
    for sz in sizes:
        f = font(sz, bold)
        if sum(text_w(draw, s, f) for s, _ in runs) <= max_w:
            return f
    return font(sizes[-1], bold)


def banner(width: int, number: int, title: str, runs: Sequence[Tuple[str, Tuple[int, int, int]]],
           subtitle: str = "") -> Image.Image:
    """Big tile number, a title and a ONE-LINE legend, baked in."""
    im = Image.new("RGB", (width, 236), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 190, 176], fill=INK)
    nf = font(130 if number < 100 else 100)
    nw = text_w(d, str(number), nf)
    d.text(((190 - nw) / 2, 12), str(number), font=nf, fill=(255, 255, 255))
    d.text((214, 22 if subtitle else 40), title, font=font(58), fill=INK)
    if subtitle:
        d.text((214, 100), subtitle, font=font(40, False), fill=INK)
    lf = fit_runs(d, runs, width - 24)
    x = 12
    for s, col in runs:
        d.text((x, 190), s, font=lf, fill=col)
        x += text_w(d, s, lf)
    d.line([0, 233, width, 233], fill=(190, 190, 190), width=3)
    return im


def staff_label(draw: ImageDraw.ImageDraw, x: int, y_bottom: int, line1: str, line2: str,
                color: Tuple[int, int, int]) -> None:
    """A white label with a coloured border whose bottom edge sits at ``y_bottom``."""
    f1, f2 = font(46), font(34)
    w = int(max(text_w(draw, line1, f1), text_w(draw, line2, f2))) + 24
    h = 46 + 34 + 26
    top = y_bottom - h
    draw.rectangle([x, top, x + w, y_bottom], fill=(255, 255, 255), outline=color, width=5)
    draw.text((x + 12, top + 6), line1, font=f1, fill=color)
    draw.text((x + 12, top + 6 + 48), line2, font=f2, fill=color)


def staff_lines(draw: ImageDraw.ImageDraw, ys: Sequence[float], width: int, color, thick: int) -> None:
    for y in ys:
        draw.rectangle([0, y - thick / 2, width, y + thick / 2], fill=color)


def corner_brackets(draw: ImageDraw.ImageDraw, rect: Tuple[float, float, float, float], color=RED,
                    thick: int = 10, arm: int = 46) -> None:
    x0, y0, x1, y1 = rect
    for x, y, sx, sy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        draw.line([x, y, x + sx * arm, y], fill=color, width=thick)
        draw.line([x, y, x, y + sy * arm], fill=color, width=thick)


def compose(top: Image.Image, body: Image.Image, bottom: Optional[Image.Image] = None) -> Image.Image:
    parts: List[Image.Image] = [p for p in (top, body, bottom) if p is not None]
    out = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts)), (255, 255, 255))
    y = 0
    for p in parts:
        out.paste(p, (0, y))
        y += p.height
    return out


def _palette() -> Image.Image:
    """32 grey levels (the print) plus the EXACT drawing colours, so orange stays orange and red stays red."""
    cols = [(g, g, g) for g in range(0, 256, 8)] + [(255, 255, 255), ORANGE, GREY, RED, GREEN, BLUE, INK]
    flat = [c for rgb in cols for c in rgb]
    flat += [0] * (768 - len(flat))
    pal = Image.new("P", (1, 1))
    pal.putpalette(flat)
    return pal


def save_small(im: Image.Image, path, colors: int = 0) -> None:
    """Palette PNG: crisp, flat colours, a fraction of the bytes (92 tiles go in the repo)."""
    im.convert("RGB").quantize(palette=_palette(), dither=Image.NONE).save(str(path), optimize=True)
