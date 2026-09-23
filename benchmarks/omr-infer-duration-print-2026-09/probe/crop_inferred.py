"""ROADMAP 2.3 — a print crop for every duration the INFER stage would write.

`collapse_duration_by_column` and `collapse_duration_to_barline` are both
default OFF, and `benchmarks/omr-infer-default-2026-09/FINDINGS.md`'s own
table gives the reason in four words: **"no note checked against a page"**.
This cuts one crop per inference so that sentence can stop being true.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL (`omr-stem-crop-pass-2026-09`'s
precedent, reused by 2.4a). The record's boxes are filed against a raster;
if the page this script renders is not that raster, nothing drawn on it is
evidence. The control: the staff's own `Q.STAFF_LINES` rows must be
materially DARKER than a half-space offset from them. A page that fails is
REFUSED, not cropped with a caveat.

⚠️ THE SUBJECT IS MARKED WITH CORNER BRACKETS ON THE EXACT HEAD, never a
margin tick at its x (CLAUDE.md 6b). A ruler of staff spaces is drawn beside
it so the reader can measure rather than judge.

⚠️ WHAT THE CROP CAN AND CANNOT SETTLE. It shows the printed note and its
flag/beam, which is what a duration IS. It does NOT show whether the rule's
WITNESSES were right -- that is a different question and needs their crops
too, which is why `--witnesses` also cuts those.

    python3 probe/crop_inferred.py --arm <reinfer --out file> \
        --pdf <edition.pdf> --label litolff --dpi 600 --out-dir out/print
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402

DURATION_RULES = ("collapse_duration_by_column", "collapse_duration_to_barline")


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    """The staff lines must be darker than a half-space off them, or this
    render is not the record's frame. Returns (ok, contrast)."""
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


def _index(rec):
    """(quantity, subject) -> value, for the quantities this probe reads."""
    want = {"glyph_box", "cell_box", "cell_staff_space", "staff_lines",
            "staff_spacing", "notehead_class", "glyph_conf"}
    out = {}
    for o in rec["observations"]:
        if o["quantity"] in want:
            out[(o["quantity"], o["subject"])] = o["value"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, help="reinfer.py --out file")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", default="out/print")
    ap.add_argument("--pad-spaces", type=float, default=9.0,
                    help="crop half-width in STAFF SPACES around the subject")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.arm)
    rec, inf = d["record"], d["inference"]
    vby = {v["id"]: v for v in rec["verdicts"]}
    idx = _index(rec)

    jobs = [(r, s, v) for r, s, v in inf["inferred"] if r in DURATION_RULES]
    print(f"{len(jobs)} duration inferences to crop")

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames = {}, {}
    manifest, refused = [], []

    for rule, subj, vid in jobs:
        _, p, sy, st, ce, gi = subj.split("/")
        p, sy, st, ce = int(p), int(sy), int(st), int(ce)
        cell = f"cell/{p}/{sy}/{st}/{ce}"
        staff = f"staff/{p}/{sy}/{st}"
        gbox = idx.get(("glyph_box", subj))
        cbox = idx.get(("cell_box", cell))
        css = idx.get(("cell_staff_space", cell))
        lines = idx.get(("staff_lines", staff))
        spacing = idx.get(("staff_spacing", staff))
        if not all((gbox, cbox, css, lines, spacing)):
            refused.append({"subject": subj, "why": "geometry missing"})
            continue

        if p not in pages:
            pm = doc[p].get_pixmap(dpi=a.dpi)
            im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples) \
                if pm.n >= 3 else Image.frombytes("L", (pm.width, pm.height), pm.samples).convert("RGB")
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        im, arr = pages[p], frames[p]

        ok, contrast = _frame_ok(arr, lines, spacing)
        if not ok:
            refused.append({"subject": subj, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        # canonical cell frame -> page pixels
        scale = float(spacing) / float(css)
        gx, gy, gw, gh = gbox[1], gbox[2], gbox[3], gbox[4]
        px0 = cbox[0] + gx * scale
        py0 = cbox[1] + gy * scale
        px1 = px0 + gw * scale
        py1 = py0 + gh * scale

        pad = a.pad_spaces * float(spacing)
        cx0, cy0 = int(max(0, px0 - pad)), int(max(0, py0 - pad * 0.8))
        cx1, cy1 = int(min(im.width, px1 + pad)), int(min(im.height, py1 + pad * 0.8))
        crop = im.crop((cx0, cy0, cx1, cy1))
        Z = 4
        crop = crop.resize(((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        # corner brackets on the EXACT head
        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        arm_len = max(6, int((bx1 - bx0) * 0.35))
        R, W = (220, 0, 0), 2
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=R, width=W)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=R, width=W)

        # a ruler: one tick per staff space down the left edge
        step = float(spacing) * Z
        y = (lines[0] - cy0) * Z
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 22, y)], fill=(0, 90, 200), width=1)
            y += step
            k += 1

        v = vby[vid]
        prior = vby.get(v.get("supersedes"))
        name = f"{a.label}-p{p}-s{sy}-st{st}-c{ce}-g{gi}-{rule.split('_')[-1]}.png"
        crop.save(out_dir / name)
        manifest.append({
            "file": name, "subject": subj, "rule": rule,
            "inferred_beats": (v.get("value") or {}).get("beats"),
            "inferred": v.get("value"), "reason": v.get("reason"),
            "candidates": (prior or {}).get("candidates"),
            "picked_lower_support": _picked_lower(v, prior),
            "notehead_class": idx.get(("notehead_class", subj)),
            "detector_conf": idx.get(("glyph_conf", subj)),
            "page": p, "system": sy, "staff": st, "cell": ce,
            "frame_contrast": round(contrast, 2),
            "page_box": [round(px0, 1), round(py0, 1), round(px1, 1), round(py1, 1)],
            "VERDICT_none_yet": None,
        })

    (out_dir / f"crop-manifest-{a.label}.json").write_text(
        json.dumps({"crops": manifest, "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    lower = [m for m in manifest if m["picked_lower_support"]]
    print(f"⚠️ {len(lower)} of {len(manifest)} pick the LOWER-support candidate "
          f"-- the cases where the rule overrides the reader's own ordering, "
          f"and the ones worth reading first")
    return 0


def _picked_lower(v, prior):
    if not prior or not prior.get("candidates"):
        return None
    cands = prior["candidates"]
    best = max(c.get("support", 0) for c in cands)
    for c in cands:
        if c.get("value") == v.get("value"):
            return c.get("support", 0) < best
    return None


if __name__ == "__main__":
    raise SystemExit(main())
