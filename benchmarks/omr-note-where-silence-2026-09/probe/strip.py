"""ONE PRINTED STAFF, END TO END, with what we exported written under each bar.

A single suspect crop cannot answer *"does the page print silence here"*, because
the answer is comparative: the bar next door, on the SAME staff and the same
print quality, is the only fair control for this one. So this renders a whole
staff-system as a strip and labels every bar with what our file says stands in
it -- `.` for a bar we wrote a rest in, the pitch for a lone note, `N` for a bar
with several events.

⚠️ It draws OUR reading onto THE PRINT and nothing more. Where the two disagree
the print wins; that is the whole point of looking.

⚠️ The strip is cut in TWO halves by default because a 2,000 px staff squeezed
to one image is unreadable at the size a reader actually sees -- and an
unreadable crop is a dead instrument that looks alive.

    python3 .../strip.py --cache cache.json --xml FILE --map system-map.json \
        --page 4 --system 0 --staff 0 --out-dir D
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from population import bars as parse_bars          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--xml", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, required=True)
    ap.add_argument("--staff", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--above", type=float, default=7.0)
    ap.add_argument("--below", type=float, default=7.0)
    ap.add_argument("--chunks", type=int, default=2)
    ap.add_argument("--target-px", type=float, default=240.0)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page

    cache = json.load(open(a.cache))
    skey = f"staff/{a.page}/{a.system}/{a.staff}"
    lines = spacing = None
    cellb = {}
    boxes, cls, rest = {}, {}, {}
    for o in cache["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "staff_lines" and s == skey:
            lines = o["value"]
        elif q == "staff_spacing" and s == skey:
            spacing = o["value"]
        elif q == "cell_box":
            cellb[s] = (o.get("detail") or {}).get("bbox_page_px") or o["value"]
        elif q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                boxes[s] = pb
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
    if not lines or not spacing:
        print(f"NO STAFF GEOMETRY for {skey} -- dead instrument", file=sys.stderr)
        return 2

    # which exported measures belong to this printed staff
    row = None
    for s in json.load(open(a.map))["systems"]:
        if s["page"] == a.page and s["system"] == a.system:
            for st in s["staves"]:
                if st["staff"] == a.staff:
                    row = st
    if row is None:
        print("staff not in the system map -- dead instrument", file=sys.stderr)
        return 2
    content = {}
    for b in parse_bars(a.xml):
        if b["part"] == row["part_id"]:
            content[b["measure"]] = b

    pi = render_page(a.pdf, a.page, dpi=a.dpi)
    base = Image.fromarray(np.asarray(pi.rgb)).convert("RGB")
    top, bot = min(lines), max(lines)
    y0 = top - a.above * spacing
    y1 = bot + a.below * spacing

    cells = sorted(
        ((int(k.split("/")[4]), v) for k, v in cellb.items()
         if k.startswith(f"cell/{a.page}/{a.system}/{a.staff}/")),
        key=lambda t: t[0])
    if not cells:
        print("no cell boxes for this staff -- dead instrument", file=sys.stderr)
        return 2
    x0 = min(c[1][0] for c in cells)
    x1 = max(c[1][2] for c in cells)

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    span = (x1 - x0) / a.chunks
    made = 0
    for ci in range(a.chunks):
        cx0, cx1 = x0 + ci * span, x0 + (ci + 1) * span
        crop = base.crop((int(cx0), int(y0), int(cx1), int(y1)))
        scale = max(1, int(round(a.target_px / max(1.0, y1 - y0))))
        crop = crop.resize((crop.width * scale, crop.height * scale),
                           Image.NEAREST)
        d = ImageDraw.Draw(crop)
        X = lambda v: (v - cx0) * scale
        Y = lambda v: (v - y0) * scale
        d.line([(0, Y(bot - 5.5 * spacing / 2.0)),
                (crop.width, Y(bot - 5.5 * spacing / 2.0))],
               fill=(0, 160, 0), width=1)
        for idx, cb in cells:
            if cb[2] < cx0 or cb[0] > cx1:
                continue
            d.line([(X(cb[0]), 0), (X(cb[0]), crop.height)],
                   fill=(255, 0, 255), width=1)
            n = row["first_measure"] + idx
            b = content.get(n)
            if b is None:
                label = "?"
            else:
                ev = b["events"]
                pitched = [e for e in ev if e["pitch"]]
                if not ev:
                    label = "(empty)"
                elif not pitched:
                    label = "R" if len(ev) == 1 else f"R*{len(ev)}"
                elif len(ev) == 1:
                    label = f"{pitched[0]['pitch']}/{pitched[0]['type'] or '?'}"
                else:
                    label = f"N{len(pitched)}"
            d.text((X(cb[0]) + 3, 2), f"m{n} {label}", fill=(200, 0, 0))
        name = f"p{a.page}s{a.system}st{a.staff}-{ci + 1}of{a.chunks}.png"
        crop.save(out / name)
        made += 1
        print(f"{name}  {crop.width}x{crop.height}  "
              f"measures {row['first_measure']}..{row['last_measure']}  "
              f"part {row['part_id']} ({row['part_name']})")
    return 0 if made else 2


if __name__ == "__main__":
    raise SystemExit(main())
