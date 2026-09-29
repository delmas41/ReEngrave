"""ROADMAP 2.23 -- final crop set, Litolff page 6 re-gather.

Ad hoc, explicit subject list (small population on this one page):
the one head this rule NARROWED, plus contrastive cases showing the
`beam_evidence == "none_over_this_note"` gate protecting real marked
heads from a false-positive ink reading, plus the borderline case from
the original whole-movement `F` crop (m145) that correctly abstains.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-owner-domain-2026-09"))

RECORD = HERE / "out/records/litolff-p6-2.23.record.json"
PDF = (ROOT / "library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
OUT = HERE / "out/print"
DPI = 600

JOBS = [
    ("glyph/6/1/9/2/9", "NARROWED head_fill_from_ink -- ink decisively hollow, "
     "no marks read; stayed narrowed (system's Q.METER abstains, S17a -- "
     "orthogonal, pre-existing gap, not this rule's fault)"),
    ("glyph/6/0/3/8/19", "PROTECTED: ink reads decisively hollow too, but "
     "beam_evidence=='read' (a genuine 8th note, beam present) -- the "
     "marks-gate correctly keeps this OUT of the rule's population"),
    ("glyph/6/1/11/5/3", "PROTECTED: same as above -- genuinely beamed "
     "(beats=0.5), ink's false-positive hollow reading is safely ignored"),
    ("glyph/6/0/0/9/1", "PROTECTED: ink reads decisively hollow, but "
     "beam_evidence=='reader_declined' (beam reader never ran on this "
     "cell) -- gate requires 'ran and found nothing', not 'declined'"),
    ("glyph/6/1/1/0/8", "PROTECTED: same as above -- reader_declined"),
    ("glyph/6/0/8/3/4", "The original S17b `F`-06 crop's BLACK member "
     "(m145): ink_net centre 0.60, just ABOVE the 0.5 threshold -- "
     "correctly does NOT narrow (rule 8: not decisive, left alone)"),
]


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from crop_losers_2_6b import _frame_ok

    d = json.load(open(RECORD))
    obs = d["record"]["observations"]
    staff_lines = {o["subject"]: o["value"] for o in obs if o["quantity"] == "staff_lines"}
    cell_box = {o["subject"]: o["value"] for o in obs if o["quantity"] == "cell_box"}
    glyph_box = {}
    for o in obs:
        if o["quantity"] == "glyph_box":
            bp = (o.get("detail") or {}).get("bbox_page_px")
            if bp:
                glyph_box[o["subject"]] = bp

    font = ImageFont.load_default(size=24)
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF))
    pm = doc[6].get_pixmap(dpi=DPI)
    page = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    arr = np.asarray(page.convert("L"), dtype=float)

    manifest = []
    for n, (sub, caption) in enumerate(JOBS, 1):
        parts = sub.split("/")
        p, sysn, st, c, gi = parts[1:]
        skey = f"staff/{p}/{sysn}/{st}"
        ckey = f"cell/{p}/{sysn}/{st}/{c}"
        if skey not in staff_lines or ckey not in cell_box or sub not in glyph_box:
            manifest.append({"n": n, "subject": sub, "refused": "no geometry"})
            continue
        lines = staff_lines[skey]
        spacing = (lines[-1] - lines[0]) / 4.0
        ok, contrast = _frame_ok(arr, lines, spacing)
        cbox = cell_box[ckey]
        gbox = glyph_box[sub]
        pad = spacing * 4.0
        x0 = max(0, int(cbox[0] - pad // 2))
        x1 = min(page.width, int(cbox[2] + pad // 2))
        y0 = max(0, int(lines[0] - spacing * 2.5))
        y1 = min(page.height, int(lines[-1] + spacing * 2.5))
        crop = page.crop((x0, y0, x1, y1)).convert("RGB")
        draw = ImageDraw.Draw(crop)
        for ly in lines:
            yy = ly - y0
            draw.line([(0, yy), (crop.width, yy)], fill=(0, 160, 0), width=2)
        for cx in (cbox[0], cbox[2]):
            draw.line([(cx - x0, 0), (cx - x0, crop.height)], fill=(220, 0, 0), width=2)
        gx0, gy0, gx1, gy1 = gbox
        L = 12
        for (cx, cy, sx, sy) in ((gx0, gy0, 1, 1), (gx1, gy0, -1, 1),
                                 (gx0, gy1, 1, -1), (gx1, gy1, -1, -1)):
            cx -= x0; cy -= y0
            draw.line([(cx, cy), (cx + L * sx, cy)], fill=(220, 0, 0), width=3)
            draw.line([(cx, cy), (cx, cy + L * sy)], fill=(220, 0, 0), width=3)
        band = Image.new("RGB", (crop.width, crop.height + 90), (255, 255, 255))
        band.paste(crop, (0, 90))
        bd = ImageDraw.Draw(band)
        bd.text((4, 4), f"#{n} {sub}  frame_contrast={contrast:.1f} ok={ok}",
                fill=(0, 0, 0), font=font)
        import textwrap
        for i, line in enumerate(textwrap.wrap(caption, 90)):
            bd.text((4, 28 + i * 20), line, fill=(0, 0, 0), font=font)
        fname = f"head-fill-2026-09-{n:02d}.png"
        band.save(OUT / fname)
        manifest.append({"n": n, "subject": sub, "file": fname,
                         "frame_contrast": round(contrast, 2), "frame_ok": ok,
                         "caption": caption, "VERDICT_none_yet": None})

    with open(OUT / "head-fill-2026-09-manifest.json", "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"wrote {len(manifest)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
