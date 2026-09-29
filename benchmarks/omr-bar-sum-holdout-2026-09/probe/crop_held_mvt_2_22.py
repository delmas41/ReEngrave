"""ROADMAP 2.22 -- banded crops of held bars at movement scale.

`crop_held_2_19.py`'s drawing, fed from files instead of a record load: the
geometry `reconcile_why_2_22.py` wrote beside its output
(`*.geometry.json`: `Q.STAFF_LINES`/`Q.STAFF_SPACING` page frame,
`Q.CELL_BOX`, each glyph's `bbox_page_px`) and a jobs file
`[{"name", "cell": [p, s, st, c], "subjects": [glyph keys], "says"}]`.
The page is rendered straight off the PDF at the gather's DPI (600); the
record's `page` is the PDF page index.

⚠️ FRAME CONTROL FIRST (`crop_losers_2_6b._frame_ok`, imported): a crop
whose filed staff's lines are not darker than a half-space off them is
REFUSED, not drawn. GREEN band = the staff the bar is filed on, lines drawn;
red verticals = the cell's x-span; red corners = the subject boxes.

    python3 .../crop_held_mvt_2_22.py <geometry.json> <jobs.json> <pdf> <prefix> [zoom]
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks/omr-owner-domain-2026-09"))

OUT = HERE.parent / "out" / "print"
DPI = 600


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from crop_losers_2_6b import _frame_ok

    geom_path, jobs_path, pdf, prefix = sys.argv[1:5]
    g = json.load(open(geom_path))
    jobs = json.load(open(jobs_path))
    lines, spacing = g["staff_lines"], g["staff_spacing"]
    cbox, gbox = g["cell_box"], g["glyph_page_px"]
    font = ImageFont.load_default(size=26)
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    pages = {}
    manifest = []
    for n, job in enumerate(jobs, 1):
        p, s, st, c = job["cell"]
        skey, ckey = f"staff/{p}/{s}/{st}", f"cell/{p}/{s}/{st}/{c}"
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            img = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
            pages[p] = (img, np.asarray(img.convert("L"), dtype=float))
        page, arr = pages[p]
        if skey not in lines or ckey not in cbox:
            manifest.append({"n": n, "name": job["name"], "cell": ckey,
                             "refused": "no geometry on the record"})
            continue
        ok, contrast = _frame_ok(arr, lines[skey], spacing[skey])
        if not ok:
            manifest.append({"n": n, "name": job["name"], "cell": ckey,
                             "refused": f"FRAME CONTROL FAILED {contrast:.1f}"})
            continue
        x0, _y0, x1, _y1 = cbox[ckey]
        sp = spacing[skey]
        ys = lines[skey]
        cy0, cy1 = int(min(ys) - 6 * sp), int(max(ys) + 6 * sp)
        cx0, cx1 = int(x0 - 3 * sp), int(x1 + 3 * sp)
        cx0, cy0 = max(0, cx0), max(0, cy0)
        Z = int(sys.argv[5]) if len(sys.argv) > 5 else 2
        crop = page.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        top, bot = (min(ys) - cy0) * Z, (max(ys) - cy0) * Z
        od.rectangle([0, top, crop.width, bot], fill=(0, 170, 60, 50))
        for y in ys:
            od.line([0, (y - cy0) * Z, crop.width, (y - cy0) * Z],
                    fill=(0, 170, 60, 200), width=2)
        for xx in (x0, x1):
            od.line([(xx - cx0) * Z, 0, (xx - cx0) * Z, crop.height],
                    fill=(220, 0, 0, 200), width=3)
        for sub in job.get("subjects") or []:
            if sub not in gbox:
                continue
            bx0, by0, bx1, by1 = gbox[sub][1]
            X0, Y0 = (bx0 - cx0) * Z - 4, (by0 - cy0) * Z - 4
            X1, Y1 = (bx1 - cx0) * Z + 4, (by1 - cy0) * Z + 4
            L = 12
            for a, b in (((X0, Y0), (X0 + L, Y0)), ((X0, Y0), (X0, Y0 + L)),
                         ((X1, Y1), (X1 - L, Y1)), ((X1, Y1), (X1, Y1 - L))):
                od.line([a, b], fill=(220, 0, 0, 255), width=3)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        W = max(crop.width, 1100)
        text = [f"#{n} {ckey}  GREEN = filed staff {skey}",
                "red verticals = the bar's Q.CELL_BOX x-span; red corners = "
                "subject boxes"]
        text += textwrap.wrap(job["says"], width=int(W / 14))
        hh = 8 + 34 * len(text)
        head = Image.new("RGB", (W, hh), "white")
        hd = ImageDraw.Draw(head)
        for i, t in enumerate(text):
            hd.text((8, 6 + 34 * i), t, fill="black", font=font)
        sheet = Image.new("RGB", (W, crop.height + hh), "white")
        sheet.paste(head, (0, 0))
        sheet.paste(crop, (0, hh))
        fn = f"{prefix}-{n:02d}-{job['name']}.png"
        sheet.save(OUT / fn)
        manifest.append({"n": n, "file": fn, "cell": ckey,
                         "subjects_bracketed": job.get("subjects") or [],
                         "record_says": job["says"],
                         **{k: v for k, v in job.items()
                            if k not in ("name", "cell", "subjects", "says")},
                         "frame_contrast": round(contrast, 1),
                         "VERDICT_none_yet": None})
        print("wrote", fn)
    (OUT / f"{prefix}-manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
