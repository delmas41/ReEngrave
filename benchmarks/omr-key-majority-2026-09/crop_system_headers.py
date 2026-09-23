"""ONE CROP PER SYSTEM HEADER, for Sean to confirm the plate's keys at a look.

    python3 benchmarks/omr-key-majority-2026-09/crop_system_headers.py \
        --record <record.json> --pdf <edition.pdf> --page 3 --dpi 600 \
        --label litolff --out-dir benchmarks/omr-key-majority-2026-09/out/print

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL (`omr-stem-crop-pass-2026-09`'s
precedent). The record's geometry is filed against a raster; if the page this
script renders is not that raster then nothing drawn on it is evidence. The
control: every staff's own `Q.STAFF_LINES` rows must be materially DARKER
than a half-space off them. A system that fails is REFUSED and not cropped.

⚠️ THE SUBJECT IS MARKED, AND THE SUBJECT HERE IS THE HEADER OF EACH STAFF —
so each staff's own five recorded lines are traced across the crop and its
name is printed at its own left margin. Sean, 2026-09-23, on the first
duration crops: *"there is a staff at the top and a staff at the bottom - i
dont know which staff the cell is focussing on."* A crop that does not say
what it is about is not evidence.

⚠️ WHAT IT ASKS AND WHAT IT CANNOT ASK. It shows what the PLATE prints at the
head of every staff of one system. It cannot show whether the concert key is
right — that needs the instrument, which is why each row prints the name our
file gives that staff beside the fifths we wrote. The manifest carries
`VERDICT_none_yet: null` until a human fills it in.

⚠️ NO DEFAULT IS FLIPPED BY THIS SCRIPT AND IT DECIDES NOTHING.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402


def _fields(key: str):
    head, *rest = key.split("/")
    nums = [int(x) if x.isdigit() else None for x in rest]
    while len(nums) < 4:
        nums.append(None)
    return head, nums[0], nums[1], nums[2], nums[3]


def _font(size: int):
    """A legible caption font, or PIL's bitmap default.

    ⚠️ The default is ~11 px on a 1400-px-wide crop, which makes the caption
    unreadable at the size the image is actually looked at — and a crop whose
    caption cannot be read does not say what it is about."""
    from PIL import ImageFont
    for path in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                 "/System/Library/Fonts/Helvetica.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:                                      # noqa: BLE001
            continue
    return ImageFont.load_default()


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    """The staff lines must be darker than a half-space off them."""
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True, help="PDF page index")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--label", required=True)
    ap.add_argument("--out-dir", default=str(HERE / "out" / "print"))
    ap.add_argument("--header-spaces", type=float, default=26.0,
                    help="crop width from the first cell's left edge")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.record)
    rec = d["record"]
    lines, spacing, label, cellbox = {}, {}, {}, {}
    for o in rec["observations"]:
        _, p, s, st, c = _fields(o["subject"])
        if p != a.page:
            continue
        q = o["quantity"]
        if q == "staff_lines":
            lines[(s, st)] = o["value"]
        elif q == "staff_spacing":
            spacing[(s, st)] = float(o["value"])
        elif q == "margin_label":
            label[(s, st)] = str(o["value"])
        elif q == "cell_box" and c == 0:
            cellbox[(s, st)] = o["value"]
    key, name, sysverdict = {}, {}, {}
    for v in rec["verdicts"]:
        _, p, s, st, _ = _fields(v["subject"])
        if p != a.page:
            continue
        if v["quantity"] == "key_signature":
            key[(s, st)] = (v["outcome"], v.get("value"), v.get("reason"))
        elif v["quantity"] == "part_name":
            name[(s, st)] = v.get("value")
        elif v["quantity"] == "system_key":
            sysverdict[s] = v.get("value")

    systems = sorted({s for (s, _st) in lines})
    if not systems:
        print(f"DEAD: the record holds no staff geometry on page {a.page} — "
              f"nothing to crop, which is not the same as a clean page")
        return 2

    out_dir = pathlib.Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pm = doc[a.page].get_pixmap(dpi=a.dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB"))
    arr = np.asarray(im.convert("L"), dtype=float)

    manifest, refused = [], []
    for s in systems:
        staves = sorted(st for (sy, st) in lines if sy == s)
        ys = [y for st in staves for y in lines[(s, st)]]
        sp = spacing.get((s, staves[0]), 0.0)
        if not ys or sp <= 0:
            refused.append({"system": s, "why": "geometry missing"})
            continue
        ok, contrast = _frame_ok(arr, ys, sp)
        if not ok:
            refused.append({"system": s, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue
        boxes = [cellbox[(s, st)] for st in staves if (s, st) in cellbox]
        x_left = min(b[0] for b in boxes) if boxes else 0
        # ⚠️ ENOUGH LEFT MARGIN TO SHOW THE PRINTED STAFF NAME. The first
        # version cut at 6 spaces and clipped "Flute 1" to "lute 1" — the
        # crop then cannot be read against the plate without the record's own
        # answer, which is the one thing it must not depend on.
        x0 = int(max(0, x_left - 16 * sp))
        x1 = int(min(im.width, x_left + a.header_spaces * sp))
        y0 = int(max(0, min(ys) - 3 * sp))
        y1 = int(min(im.height, max(ys) + 3 * sp))
        crop = im.crop((x0, y0, x1, y1))
        Z = 2
        crop = crop.resize(((x1 - x0) * Z, (y1 - y0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)
        for st in staves:
            for ly in lines[(s, st)]:
                y = (ly - y0) * Z
                if 0 <= y < crop.height:
                    dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60),
                            width=1)
        # a ruler of staff spaces down the left edge, so the reader measures
        step = sp * Z
        y, k = (min(ys) - y0) * Z, 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 24, y)], fill=(0, 90, 200),
                        width=1)
            y += step
            k += 1

        rows = []
        for st in staves:
            outcome, value, reason = key.get((s, st), ("-", None, "-"))
            who = name.get((s, st)) or label.get((s, st)) or "?"
            rows.append(f"staff {st:>2}  {str(who)[:22]:<24} "
                        f"we wrote {('' if value is None else value)!s:>3}"
                        f"   ({outcome}/{reason})")
        font = _font(22)
        line_h = 26
        band_h = line_h * (len(rows) + 4)
        out_im = Image.new("RGB", (max(crop.width, 1100),
                                   crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((8, 4), f"{a.label}  pdf page {a.page}  system {s}  "
                        f"dpi {a.dpi}  frame contrast {contrast:.1f}  "
                        f"verdicts from {pathlib.Path(a.record).name}",
                fill=(0, 0, 0), font=font)
        cd.text((8, 4 + line_h),
                "QUESTION: how many sharps/flats does the PLATE print at the "
                "head of each staff?", fill=(140, 0, 0), font=font)
        cd.text((8, 4 + 2 * line_h),
                f"system_key (concert, ours): {json.dumps(sysverdict.get(s))}",
                fill=(0, 90, 200), font=font)
        for i, line in enumerate(rows):
            cd.text((8, 4 + (3 + i) * line_h), line, fill=(0, 120, 45),
                    font=font)
        dest = out_dir / f"{a.label}-p{a.page}-system{s}-header.png"
        out_im.save(dest)
        manifest.append({
            "file": dest.name, "label": a.label, "pdf_page": a.page,
            "system": s, "dpi": a.dpi, "frame_contrast": round(contrast, 2),
            "staves": [{"staff": st,
                        "name_our_file_gives_it":
                            name.get((s, st)) or label.get((s, st)),
                        "we_wrote_fifths": key.get((s, st), ("-", None, "-"))[1],
                        "outcome": key.get((s, st), ("-", None, "-"))[0],
                        "reason": key.get((s, st), ("-", None, "-"))[2]}
                       for st in staves],
            "system_key_concert_ours": sysverdict.get(s),
            # ⚠️ WHICH RECORD THE CAPTION'S FIFTHS CAME FROM. The plate's own
            # answer is the question and does not depend on this — but "we
            # wrote" does, and a crop cut from the shipped record and one cut
            # from an arm say different things under the same heading.
            "verdicts_from": a.record,
            # ⚠️ NOT A VERDICT. Nothing here has been adjudicated against the
            # print; this key exists so that the file cannot be read as if it
            # had been.
            "VERDICT_none_yet": None})
    (out_dir / f"{a.label}-p{a.page}-manifest.json").write_text(
        json.dumps({"crops": manifest, "refused": refused}, indent=1))
    print(f"{len(manifest)} crops, {len(refused)} refused -> {out_dir}")
    for r in refused:
        print("   refused:", r)
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
