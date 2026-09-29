"""ROADMAP 2.24 -- print crops for the diagnosis of the `D` (one-dot) held-bar
class on Breitkopf Brahms 1/i pdf idx 1 (the fresh single-page record
`out/r224/brahms-p1.record.json`).

Frame control is `crop_losers_2_6b._frame_ok`'s precedent (staff-line
contrast on vs off the line, margin 8.0); a crop that fails it is refused and
named in the manifest's `refused` list.

Every crop's SUBJECT (a dot glyph, a refused notehead, or -- where nothing
was gathered at all -- the bar's own empty region) is bracketed RED. The
staff the subject is filed on is banded and its lines drawn, per
`feedback_send_sean_the_crop` (2026-09-23): a crop must name the staff and
draw its lines, never leave the subject in the gap between two.

    python3 benchmarks/omr-bar-sum-holdout-2026-09/probe/crop_dots_2_24.py
"""
from __future__ import annotations

import json
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[3]
PDF = Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
           "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--"
           "imslp317803.pdf")
OUT_DIR = Path(__file__).resolve().parents[1] / "out/print"
DPI = 600


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    c = float(sum(off) / len(off) - sum(on) / len(on))
    return c >= margin, c


JOBS = [
    dict(name="dot24-01", page=1, staff="staff/1/0/2", lines=[1046, 1073, 1101, 1128, 1156],
         subject_box=[4646.5, 1054.9, 4659.9, 1068.1], subject="glyph/1/0/2/5/18",
         crop=[4420, 970, 4770, 1220],
         title="#01 cell 1/0/2/5 (m.6 P3) -- dot glyph 18, DECIDED augmentation",
         caption="Paired to the InSpace head above (right of + level with it). Control: this is the window working."),
    dict(name="dot24-02", page=1, staff="staff/1/0/2", lines=[1046, 1073, 1101, 1128, 1156],
         subject_box=[4645.9, 1166.4, 4660.2, 1181.3], subject="glyph/1/0/2/5/31",
         crop=[4420, 970, 4770, 1220],
         title="#02 SAME cell -- dot glyph 31, ABSTAINED dot_role_ambiguous",
         caption="Q: is this an augmentation dot for the tied OnLine head above it, pushed low by the tie -- or is it the tie's own ink, misboxed as a dot?"),
    dict(name="dot24-03", page=1, staff="staff/1/0/10", lines=[2961, 2989, 3016, 3043, 3071],
         subject_box=[3300.375, 2918.1, 3310.0, 2926.075], subject="glyph/1/0/10/3/32",
         crop=[3060, 2850, 3420, 3010],
         title="#03 cell 1/0/10/3 (m.4 P11) -- dot glyph 32, ABSTAINED",
         caption="This sits just right of the direction word 'espr.' (arco below it), not beside any notehead -- the abbreviation's own period, boxed augmentationDot."),
    dict(name="dot24-04", page=1, staff="staff/1/0/11", lines=[3286, 3313, 3340, 3368, 3396],
         subject_box=[3302.575, 3194.425, 3310.825, 3202.125], subject="glyph/1/0/11/3/26",
         crop=[3060, 3150, 3420, 3280],
         title="#04 cell 1/0/11/3 (m.4 P12) -- dot glyph 26, ABSTAINED, SAME pattern",
         caption="Second instance of #03's pattern one staff down -- the SAME 'espr.' label's period, systemic rather than one-off."),
    dict(name="dot24-05", page=1, staff="staff/1/1/12", lines=[6967, 6994, 7022, 7049, 7077],
         subject_box=[3632.568, 6990.13, 3653.309, 7010.03], subject="glyph/1/1/12/4/4",
         crop=[3440, 6920, 3970, 7100],
         title="#05 cell 1/1/12/4 (m.12 P14) -- NO augmentationDot row anywhere in this cell",
         caption="classify_held_mvt_2_22.py names 'D' (add one dot) for this bar's 0.5q shortfall; the only refused glyph here is this ledgered notehead, refused not_a_notehead:too_narrow, with no computed duration -- D is a numeric coincidence, not a dot."),
    dict(name="dot24-06", page=1, staff="staff/1/0/3", lines=[1358, 1384, 1412, 1439, 1467],
         subject_box=[3166.79, 1310.0, 3503.6, 1405.1], subject="cell/1/0/3/3",
         crop=[3120, 1270, 3560, 1460],
         title="#06 cell 1/0/3/3 (m.4 P4) -- NO augmentationDot row anywhere in this cell",
         caption="Another 'D'-named bar with zero dot ink gathered anywhere in it -- same coincidence as #05, different refusal family (duration_narrowed / not_a_notehead:too_narrow, both empty of candidates)."),
    dict(name="dot24-07", page=1, staff="staff/1/1/11", lines=[6754, 6780, 6807, 6835, 6863],
         subject_box=[4854.7325, 6743.9175, 4868.3575, 6756.4525], subject="glyph/1/1/11/6/5",
         crop=[4520, 6700, 4900, 6870],
         title="#07 cell 1/1/11/6 (m.14 P13) -- dot glyph 5, DECIDED augmentation (well-evidenced)",
         caption="classify's tied minimal set ('MDF') offers removing THIS decided dot as one way to hit the target sum; the companion voice's own head-fill (F) is the more likely real fix. Removing a DECIDED dot is not a repair."),
]


def main() -> int:
    font = ImageFont.load_default(size=20)
    big = ImageFont.load_default(size=34)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF))
    manifest, refused = [], []

    for j in JOBS:
        pm = doc[j["page"]].get_pixmap(dpi=DPI)
        im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
        arr = np.asarray(im.convert("L"), dtype=float)
        lines = j["lines"]
        spacing = (lines[-1] - lines[0]) / 4.0
        ok, contrast = _frame_ok(arr, lines, spacing)
        if not ok:
            refused.append({"name": j["name"], "subject": j["subject"],
                            "why": f"FRAME CONTROL FAILED contrast={contrast:.1f}"})
            continue

        cx0, cy0, cx1, cy1 = j["crop"]
        crop = im.crop((cx0, cy0, cx1, cy1))
        Z = 3
        crop = crop.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)

        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        top = (min(lines) - cy0) * Z
        bot = (max(lines) - cy0) * Z
        od.rectangle([0, top, crop.width, bot], fill=(0, 170, 60, 55))
        for ly in lines:
            y = (ly - cy0) * Z
            if 0 <= y < crop.height:
                od.line([(0, y), (crop.width, y)], fill=(0, 170, 60, 230), width=4)
        label = j["staff"]
        tw = od.textlength(label, font=big)
        ty = max(0, top - big.size - 4)
        od.rectangle([6, ty - 2, 6 + tw + 10, ty + big.size + 4],
                     fill=(255, 255, 255, 235), outline=(0, 170, 60, 255), width=3)
        od.text((10, ty), label, fill=(0, 120, 45, 255), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        dr = ImageDraw.Draw(crop)

        sb = j["subject_box"]
        if sb and sb[0] is not None:
            bx0, by0 = (sb[0] - cx0) * Z, (sb[1] - cy0) * Z
            bx1, by1 = (sb[2] - cx0) * Z, (sb[3] - cy0) * Z
            arm = max(14, int((bx1 - bx0) * 1.4))
            for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                     (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0), width=6)
                dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0), width=6)

        step = spacing * Z
        y = top
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (16 if k % 5 else 26, y)], fill=(0, 90, 200), width=2)
            y += step
            k += 1

        band_h = 20 * 3
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), j["title"], fill=(0, 0, 0), font=font)
        cd.text((6, 24), j["caption"], fill=(80, 0, 120), font=font)
        cd.text((6, 44), f"subject: {j['subject']}   frame contrast: {contrast:.1f}",
                fill=(0, 0, 0), font=font)
        out_name = f"{j['name']}.png"
        out_im.save(OUT_DIR / out_name)

        manifest.append({
            "n": j["name"], "file": out_name, "subject": j["subject"],
            "staff": j["staff"], "title": j["title"], "question": j["caption"],
            "frame_contrast": round(contrast, 2),
            "VERDICT_none_yet": None,
        })
        print("wrote", out_name, "contrast", round(contrast, 2))

    (OUT_DIR / "dot-2.24-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.24",
        "record": "benchmarks/omr-bar-sum-holdout-2026-09/out/r224/brahms-p1.record.json"
                    " (fresh gather, pdf idx 1, this tree, --no-surya)",
        "pdf": str(PDF) + " (machine-local, not under this worktree)",
        "dpi": DPI,
        "crops": manifest,
        "refused": refused,
    }, indent=2))
    print("total crops:", len(manifest), "refused:", len(refused))
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
