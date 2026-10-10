#!/usr/bin/env python3
"""lud_printed_numbers: crop the printed bar number at the start of each drawn
system, so a person can read it against the exporter's number.

NOT a machine reading. The record's own margin-number reader abstained or
disagreed on these systems; this montage only puts the print next to the
export's number so the difference can be read by eye (CLAUDE.md rule 3/7: the
print is the evidence, not a model's output).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lud_bars  # noqa: E402
from lud_render import font  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--item", action="append", required=True, help="doc:extract.json:page/system")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tiles = []
    for it in a.item:
        doc, ext, ps = it.split(":")
        page, sysi = (int(x) for x in ps.split("/"))
        ex = json.load(open(ext))
        off, _nb, chk, _ = lud_bars.numbering(doc)
        stv = {int(k.split("/")[3]): v for k, v in ex["staves"].items()
               if re.match(rf"^staff/{page}/{sysi}/\d+$", k)}
        top = stv[min(stv)]
        sp = (top["ys"][-1] - top["ys"][0]) / 4
        img = render_page(ex["prov"]["pdf"], page, dpi=ex["prov"]["dpi"]).rgb
        x0 = int(top["ext"][0] - 6 * sp)
        y0 = int(top["ys"][0] - 7 * sp)
        crop = Image.fromarray(img[y0:int(top["ys"][-1] + 1 * sp), x0:int(top["ext"][0] + 14 * sp)])
        sc = 3 if sp < 20 else 1.5
        crop = crop.resize((int(crop.width * sc), int(crop.height * sc)), Image.BICUBIC)
        c = chk.get((page, sysi), {})
        d = ImageDraw.Draw(crop)
        txt = (f"{doc} p{page} s{sysi}: export numbers this system's first bar {off[(page, sysi)] + 1}; "
               f"margin reader: {c.get('state')} ({c.get('printed')})")
        d.text((4, 2), txt, fill=(200, 0, 0), font=font(max(14, sp * sc * 0.55)), stroke_width=2, stroke_fill=(255, 255, 255))
        tiles.append(crop)
    W = max(t.width for t in tiles)
    H = sum(t.height for t in tiles) + 10 * len(tiles)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    y = 0
    for t in tiles:
        canvas.paste(t, (0, y))
        y += t.height + 10
    canvas.save(a.out, optimize=True)
    print(a.out, canvas.size)


if __name__ == "__main__":
    main()
