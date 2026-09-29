"""ROADMAP 2.6c (second half) — crops of heads `glyph_owner` now ABSTAINS on
`far_no_rungs` (every candidate staff two or more rungs away, no rung found
toward any), for Sean. Banded style of `crop_losers_2_6b.py`: each candidate
staff is a shaded, labelled BAND with its lines drawn thick; the head is
bracketed RED; a one-tick-per-space ruler runs off the UPPER staff.

⚠️ COLOUR FOLLOWS POSITION, NOT ROLE: GREEN is always the UPPER candidate and
ORANGE the LOWER (Sean, 2.7b.8: role colours swapped above/below between
crops and were hard to read). Neither is "the answer" -- the record declined
to choose.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL (`crop_losers_2_6b._frame_ok`,
reused): both staves' own lines must be materially darker on the render than
half a space off them, or the crop is REFUSED. `--break-frame` shifts every
line by half a space; in the real run a crop whose staves ALSO pass shifted is
refused, so every crop made has a control that failed where it had to.

    python3 benchmarks/omr-owner-domain-2026-09/crop_far_no_rungs_2_6c.py \
        --summary <readjudicate summary.json> --record <record.json> \
        --pdf <edition.pdf> --tag litolff --n 8 [--break-frame]

Record read ONLY through `record_io.load_record`.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())

from tools.omr.staged.record_io import load_record  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from crop_losers_2_6b import _frame_ok  # noqa: E402

OUT_DIR = HERE / "out" / "print"
DPI = 600
SEED = 2026092826


def main(argv=None) -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--break-frame", action="store_true")
    a = ap.parse_args(argv)

    summary = json.loads(Path(a.summary).read_text())
    far = list(summary["glyph_owner"]["far_no_rungs_subjects"])
    rng = random.Random(SEED)
    rng.shuffle(far)

    rec = load_record(a.record)["record"]
    want = set(far)
    rows = {}
    staff_keys = set()
    for o in rec["observations"]:
        if o["subject"] in want and o["quantity"] in (
                "glyph_box", "glyph_band_distance"):
            rows.setdefault(o["subject"], []).append(o)
            if o["quantity"] == "glyph_band_distance":
                staff_keys.add(o["detail"]["candidate"])
    geo = {}
    for o in rec["observations"]:
        if o["subject"] in staff_keys and o["quantity"] in (
                "staff_lines", "staff_spacing"):
            geo.setdefault(o["subject"], {})[o["quantity"]] = o["value"]

    font = ImageFont.load_default(size=20)
    doc = fitz.open(a.pdf)
    pages = {}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, refused = [], []
    for sub in far:
        if len(manifest) >= a.n:
            break
        rs = rows.get(sub, [])
        box = [o for o in rs if o["quantity"] == "glyph_box"]
        cands = [o["detail"]["candidate"] for o in rs
                 if o["quantity"] == "glyph_band_distance"]
        if not box or len(cands) != 2 or any(
                "staff_lines" not in geo.get(c, {}) for c in cands):
            refused.append({"subject": sub, "why": "geometry missing"})
            continue
        bb = box[-1]["detail"]["bbox_page_px"]
        cands.sort(key=lambda c: min(geo[c]["staff_lines"]))
        upper, lower = cands
        p = int(sub.split("/")[1])
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=DPI)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else Image.frombytes(
                      "L", (pm.width, pm.height), pm.samples).convert("RGB"))
            pages[p] = (im, np.asarray(im.convert("L"), dtype=float))
        im, arr = pages[p]
        # ⚠️ THE CONTROL MUST BE ABLE TO FAIL ON THIS VERY CROP: each
        # staff's recorded lines must pass AND the same lines shifted half a
        # space must fail. A staff that passes both is on ink dense enough
        # that the check cannot tell, and its crop is refused.
        lines, shifted = {}, {}
        for c in cands:
            sp_c = float(geo[c]["staff_spacing"])
            lines[c] = [float(y) for y in geo[c]["staff_lines"]]
            shifted[c] = [y + sp_c / 2.0 for y in lines[c]]
        ok = {c: _frame_ok(arr, lines[c], float(geo[c]["staff_spacing"]))
              for c in cands}
        broken = {c: _frame_ok(arr, shifted[c],
                               float(geo[c]["staff_spacing"]))
                  for c in cands}
        if a.break_frame:
            ok = broken
        if not all(v[0] for v in ok.values()) or (
                not a.break_frame and any(v[0] for v in broken.values())):
            refused.append({"subject": sub, "why": "FRAME CONTROL FAILED",
                            "contrast": {c: round(v[1], 1)
                                         for c, v in ok.items()},
                            "contrast_shifted": {c: round(v[1], 1)
                                                 for c, v in broken.items()}})
            continue
        sp = float(geo[upper]["staff_spacing"])
        ys = [bb[1], bb[3]] + lines[upper] + lines[lower]
        cx0 = int(max(0, bb[0] - 10 * sp))
        cx1 = int(min(im.width, bb[2] + 10 * sp))
        cy0 = int(max(0, min(ys) - 1.5 * sp))
        cy1 = int(min(im.height, max(ys) + 1.5 * sp))
        Z = 2
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        ov = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        big = ImageFont.load_default(size=max(28, int(sp * Z * 0.8)))
        for c, rgb, label in ((upper, (0, 160, 60), "GREEN - upper staff"),
                              (lower, (235, 130, 0), "ORANGE - lower staff")):
            top = (min(lines[c]) - cy0) * Z
            bot = (max(lines[c]) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=rgb + (60,))
            for ly in lines[c]:
                y = (ly - cy0) * Z
                od.line([(0, y), (crop.width, y)], fill=rgb + (230,), width=4)
            ty = max(0, top + (bot - top) / 2 - big.size / 2)
            tw = od.textlength(label, font=big)
            od.rectangle([30, ty - 4, 30 + tw + 12, ty + big.size + 6],
                         fill=(255, 255, 255, 235), outline=rgb + (255,),
                         width=4)
            od.text((36, ty), label, fill=rgb + (255,), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
        dr = ImageDraw.Draw(crop)
        bx0, by0 = (bb[0] - cx0) * Z, (bb[1] - cy0) * Z
        bx1, by1 = (bb[2] - cx0) * Z, (bb[3] - cy0) * Z
        arm = max(10, int((bx1 - bx0) * 0.45))
        for ax, ay, dx, dy in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                               (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=(220, 0, 0), width=6)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=(220, 0, 0), width=6)
        y = (min(lines[upper]) - cy0) * Z
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (16 if k % 5 else 26, y)], fill=(0, 90, 200),
                        width=2)
            y += sp * Z
            k += 1
        n = len(manifest) + 1
        name = f"2.6c-far-{a.tag}-{n:02d}.png"
        title = [
            (f"{name}  {sub}  pdf idx {p}", (0, 0, 0)),
            ("glyph_owner ABSTAINED far_no_rungs: 2+ rungs needed toward "
             "either staff, none found", (80, 0, 120)),
            ("Q: the RED-bracketed note belongs to GREEN (upper) / ORANGE "
             "(lower) / not a note? And are there ledger lines?", (0, 0, 0)),
        ]
        band = 22 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (t, col) in enumerate(title):
            cd.text((6, 4 + i * 22), t, fill=col, font=font)
        if not a.break_frame:
            out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name, "subject": sub, "page": p,
            "upper_staff": upper, "lower_staff": lower,
            "head_page_box": [round(v, 1) for v in bb],
            "frame_contrast": {c: round(v[1], 1) for c, v in ok.items()},
            "frame_contrast_shifted_half_space": {
                c: round(v[1], 1) for c, v in broken.items()},
            "question": ("which staff: GREEN (upper) / ORANGE (lower) / not "
                         "a note; and are there ledger lines toward either"),
            "VERDICT_none_yet": None})
    print(f"crops {len(manifest)}  refused {len(refused)}")
    if a.break_frame:
        return 0 if not manifest else 1
    (OUT_DIR / f"2.6c-far-{a.tag}-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.6c (second half)",
        "record": a.record, "pdf": a.pdf, "dpi": DPI, "seed": SEED,
        "population_far_no_rungs": len(far),
        "crops": manifest, "refused": refused}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
