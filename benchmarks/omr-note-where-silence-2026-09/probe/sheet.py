"""A CONTACT SHEET: every suspect's own ink, side by side, at one scale.

⚠️ Adjudicating 26 crops one at a time invites the reader to stop once a story
fits. A sheet makes the population visible at once, which is what showed that
these bars are NOT one fault -- some hold a whole rest the detector misnamed and
some hold an ordinary notehead whose bar-mates were never read.

Each panel is normalised to STAFF SPACES, not pixels, so panels from staves of
different spacing are directly comparable. The five staff lines of the panel's
OWN staff are drawn, plus a green tick at step 5.5 -- the slot an engraver must
hang a whole rest in.

⚠️ CONTROLS ARE ON THE SHEET, not in a separate run: `--controls N` prepends N
glyphs the record itself calls `restWhole` and N it calls a notehead, drawn
identically. A sheet with no controls asks the reader to recognise a whole rest
on a bitonal 1870 plate from memory.

    python3 .../sheet.py --cache cache.json --trace trace.json --pdf P \
        --out S.png [--controls 4]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PANEL_SPACES_W = 9.0
PANEL_SPACES_H = 7.0
SCALE = 14  # px per staff space in a panel; --scale overrides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--controls", type=int, default=4)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--quarters-only", action="store_true")
    ap.add_argument("--seed", type=int, default=20260915)
    ap.add_argument("--scale", type=float, default=SCALE)
    ap.add_argument("--panel-spaces", type=float, default=PANEL_SPACES_W)
    ap.add_argument("--slice", default="")
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw
    from tools.omr.preprocessing import render_page

    cache = json.load(open(a.cache))
    box, cls, rest, conf, lines, spacing = {}, {}, {}, {}, {}, {}
    for o in cache["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                box[s] = pb
        elif q == "notehead_class":
            cls[s] = o["value"]
        elif q == "rest":
            rest[s] = o["value"]
        elif q == "glyph_conf":
            conf[s] = o.get("score")
        elif q == "staff_lines":
            lines[s] = o["value"]
        elif q == "staff_spacing":
            spacing[s] = o["value"]

    rows = json.load(open(a.trace))
    if a.quarters_only:
        rows = [r for r in rows if r.get("lone_quarter_in_2_4")]
    panels = [("%s m%s" % (r["part"], r["measure"]), r["subject"]) for r in rows
              if r.get("subject")]

    rng = random.Random(a.seed)
    if a.controls:
        rw = sorted(s for s in rest if str(rest[s]).lower().startswith("restwhole")
                    and s in box)
        nh = sorted(s for s in cls if s in box)
        ctl = ([("CTRL restWhole", s) for s in rng.sample(rw, a.controls)]
               + [("CTRL notehead", s) for s in rng.sample(nh, a.controls)])
        panels = ctl + panels
    if not panels:
        print("NO PANELS -- dead instrument", file=sys.stderr)
        return 2

    pages = {}
    for _, s in panels:
        pages.setdefault(int(s.split("/")[1]), None)
    for p in list(pages):
        pages[p] = Image.fromarray(
            np.asarray(render_page(a.pdf, p, dpi=a.dpi).rgb)).convert("RGB")

    if a.slice:
        lo, hi = (int(x) for x in a.slice.split(":"))
        panels = panels[lo:hi]
    SC = a.scale
    PW_SP = a.panel_spaces
    pw, ph = int(PW_SP * SC), int(PANEL_SPACES_H * SC) + 14
    cols = a.cols
    rowsn = (len(panels) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * pw, rowsn * ph), (255, 255, 255))
    sd = ImageDraw.Draw(sheet)

    for i, (label, subj) in enumerate(panels):
        page, sysi, st = (int(x) for x in subj.split("/")[1:4])
        skey = f"staff/{page}/{sysi}/{st}"
        ly, sp = lines.get(skey), spacing.get(skey)
        b = box[subj]
        if not ly or not sp:
            continue
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        half_w, half_h = PW_SP * sp / 2.0, PANEL_SPACES_H * sp / 2.0
        crop = pages[page].crop((int(cx - half_w), int(cy - half_h),
                                 int(cx + half_w), int(cy + half_h)))
        crop = crop.resize((pw, int(PANEL_SPACES_H * SC)), Image.LANCZOS)
        d = ImageDraw.Draw(crop)
        sc = crop.height / (PANEL_SPACES_H * sp)
        Y = lambda v: (v - (cy - half_h)) * sc
        for y in ly:
            yy = Y(y)
            if 0 <= yy < crop.height:
                d.line([(0, yy), (6, yy)], fill=(0, 90, 255), width=1)
                d.line([(crop.width - 6, yy), (crop.width, yy)],
                       fill=(0, 90, 255), width=1)
        yy = Y(max(ly) - 5.5 * sp / 2.0)
        if 0 <= yy < crop.height:
            d.line([(0, yy), (crop.width, yy)], fill=(0, 170, 0), width=1)
        d.rectangle([(b[0] - (cx - half_w)) * sc, (b[1] - (cy - half_h)) * sc,
                     (b[2] - (cx - half_w)) * sc, (b[3] - (cy - half_h)) * sc],
                    outline=(255, 0, 0), width=1)
        c, r = i % cols, i // cols
        sheet.paste(crop, (c * pw, r * ph + 14))
        sd.text((c * pw + 2, r * ph + 2),
                f"{i}: {label} c{conf.get(subj, 0):.2f}", fill=(0, 0, 0))
        sd.rectangle([c * pw, r * ph, (c + 1) * pw - 1, (r + 1) * ph - 1],
                     outline=(200, 200, 200))

    sheet.save(a.out)
    print(f"{len(panels)} panels ({a.controls} restWhole + {a.controls} notehead "
          f"controls first) -> {a.out}")
    for i, (label, subj) in enumerate(panels):
        print(f"  {i:>3}  {label:<18} {subj}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
