"""ROADMAP 2.6 — a print crop for the glyphs the widened contest handed in.

⚠️⚠️ THE ONLY THING THAT CAN SAY THE NOTES WENT TO THE RIGHT STAFF. Every
number in `FINDINGS.md` is a DOMAIN measurement — how many glyphs entered a
contest and what the scoring then said. Not one of the 161 §10 counted has ever
been read against a print (§10e), and this file does not change that either: it
cuts the crops and files a `VERDICT_none_yet: null` on every row. Sean
adjudicates.

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL (`omr-stem-crop-pass-2026-09`'s
precedent, reused by 2.3 and 2.4a). The record's boxes are filed against a
raster; if the page this renders is not that raster, nothing drawn on it is
evidence. The control: the staff's own `Q.STAFF_LINES` must be materially
DARKER than a half-space off them. A page that fails is REFUSED, not cropped
with a caveat.

⚠️ THE CROP NAMES THE STAFF THE VERDICT AWARDED THE INK TO AND DRAWS THAT
STAFF'S OWN FIVE LINES IN GREEN — Sean's correction of 2026-09-23: *"there is
a staff at the top and a staff at the bottom - i dont know which staff the cell
is focussing on."* For this population that is the whole question, so the crop
also draws the staff the glyph was FILED on in blue when the two differ, and
says which is which in the caption.

⚠️⚠️ THE SAMPLE IS UNLABELLED AS TO WHICH IS WHICH, AND THAT IS DELIBERATE.
Three classes are shuffled into one numbered set: glyphs the widened contest
MOVED to a neighbour, glyphs it decided for their OWN staff, and POSITIVE
CONTROLS drawn from the contests the base arm already had (§8's 189). A batch
that says which is which cannot fail — the reader agrees with the labels. The
key is written beside the manifest, `crop-key-<label>.json`, for after.

    python3 benchmarks/omr-owner-domain-2026-09/crop_contested.py \\
        --record library/_shared-records/<record>.json \\
        --arm benchmarks/omr-owner-domain-2026-09/out/<name>.json \\
        --pdf library/editions/... --label litolff --dpi 600 \\
        --out-dir benchmarks/omr-owner-domain-2026-09/out/print
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

for _p in list(Path(__file__).resolve().parents):
    if (_p / "tools" / "omr" / "staged" / "record_io.py").exists():
        sys.path.insert(0, str(_p))
        break

from tools.omr.staged.record_io import load_record            # noqa: E402

NOTEHEAD_PREFIX = "notehead"


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--arm", required=True, help="regather_ownership.py --json")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", default="benchmarks/omr-owner-domain-2026-09/out/print")
    ap.add_argument("--moved", type=int, default=6)
    ap.add_argument("--stayed", type=int, default=6)
    ap.add_argument("--controls", type=int, default=4)
    ap.add_argument("--pad-spaces", type=float, default=9.0)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    arm = json.loads(Path(a.arm).read_text())
    rec = load_record(a.record)["record"]

    glyph = {}
    for o in rec["observations"]:
        if o["quantity"] != "glyph_box":
            continue
        d = o.get("detail") or {}
        if d.get("bbox_page_px") is None:
            continue
        glyph[o["subject"]] = (str(o["value"][0]),
                               [float(v) for v in d["bbox_page_px"]],
                               float(o.get("score") or 0.0))
    lines_of, spacing_of = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "staff_lines":
            ys = [float(y) for y in o["value"]]
            if len(ys) >= 2:
                lines_of[o["subject"]] = ys
                spacing_of[o["subject"]] = (max(ys) - min(ys)) / (len(ys) - 1)

    def own_of(sub):
        return "staff/" + "/".join(sub.split("/")[1:4])

    moved, stayed = [], []
    for sub, v in (arm.get("arm_verdicts_on_added") or {}).items():
        if sub not in glyph or not glyph[sub][0].lower().startswith(
                NOTEHEAD_PREFIX):
            continue
        if not v or v.get("outcome") != "decided" or not v.get("value"):
            continue
        (moved if v["value"] != own_of(sub) else stayed).append((sub, v))
    controls = [(s, v) for s, v in (arm.get("base_verdicts") or {}).items()
                if s in glyph and glyph[s][0].lower().startswith(NOTEHEAD_PREFIX)
                and v and v.get("outcome") == "decided" and v.get("value")
                and v["value"] != own_of(s)]

    rng = random.Random(a.seed)
    rng.shuffle(moved)
    rng.shuffle(stayed)
    rng.shuffle(controls)
    print(f"population: moved {len(moved)}  stayed {len(stayed)}  "
          f"controls available {len(controls)}")
    jobs = ([(s, v, "moved") for s, v in moved[:a.moved]]
            + [(s, v, "stayed") for s, v in stayed[:a.stayed]]
            + [(s, v, "control") for s, v in controls[:a.controls]])
    rng.shuffle(jobs)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames = {}, {}
    manifest, key, refused = [], [], []

    for n, (sub, v, kind) in enumerate(jobs, start=1):
        name, box, conf = glyph[sub]
        p = int(sub.split("/")[1])
        own = own_of(sub)
        awarded = str(v["value"])
        if awarded not in lines_of or own not in lines_of:
            refused.append({"subject": sub, "why": "staff geometry missing"})
            continue
        spacing = spacing_of[awarded]
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=a.dpi)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        im, arr = pages[p], frames[p]
        ok, contrast = _frame_ok(arr, lines_of[awarded], spacing)
        if not ok:
            refused.append({"subject": sub, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        px0, py0, px1, py1 = box
        pad = a.pad_spaces * spacing
        cx0, cy0 = int(max(0, px0 - pad)), int(max(0, py0 - pad * 1.1))
        cx1 = int(min(im.width, px1 + pad))
        cy1 = int(min(im.height, py1 + pad * 1.1))
        crop = im.crop((cx0, cy0, cx1, cy1))
        Z = 4
        crop = crop.resize(((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        # the AWARDED staff, green; the FILED staff, blue, only when different
        for ly in lines_of[awarded]:
            y = (ly - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)
        if awarded != own:
            for ly in lines_of[own]:
                y = (ly - cy0) * Z
                if 0 <= y < crop.height:
                    dr.line([(0, y), (crop.width, y)], fill=(30, 80, 220),
                            width=1)

        # corner brackets on the EXACT head
        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        arm_len = max(6, int((bx1 - bx0) * 0.35))
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=(220, 0, 0),
                    width=2)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=(220, 0, 0),
                    width=2)

        # a ruler: one tick per staff space, off the awarded staff's top line
        step = spacing * Z
        y = (lines_of[awarded][0] - cy0) * Z
        k = 0
        while y < crop.height:
            if y >= 0:
                dr.line([(2, y), (14 if k % 5 else 22, y)],
                        fill=(0, 90, 200), width=1)
            y += step
            k += 1

        band_h = 56
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"#{n:02d}   {sub}   {name}   conf {conf:.2f}",
                fill=(0, 0, 0))
        cd.text((6, 20), f"THE RECORD SAYS THIS INK BELONGS TO "
                         f"{awarded}  (GREEN lines)", fill=(0, 120, 45))
        cd.text((6, 36),
                (f"it was detected in {own}'s cell  (BLUE lines)"
                 if awarded != own else
                 "it was detected in that staff's own cell")
                + f"   |   reason: {v.get('reason')}", fill=(30, 60, 160))

        fname = f"{a.label}-{n:02d}.png"
        out_im.save(out_dir / fname)
        manifest.append({
            "n": n, "file": fname, "subject": sub, "class": name,
            "detector_conf": round(conf, 3),
            "record_says_it_belongs_to": awarded,
            "detected_in_the_cell_of": own,
            "reason": v.get("reason"),
            "frame_contrast": round(contrast, 2),
            "page_box": [round(c, 1) for c in box],
            # ⚠️ Sean fills this in. `wrong` means the ink does not belong to
            # the GREEN staff; say which staff it does belong to if you can.
            "VERDICT_none_yet": None,
        })
        key.append({"n": n, "file": fname, "subject": sub, "kind": kind})

    (out_dir / f"crop-manifest-{a.label}.json").write_text(
        json.dumps({"crops": manifest, "refused": refused}, indent=2))
    (out_dir / f"crop-key-{a.label}.json").write_text(
        json.dumps({"⚠️ DO NOT READ BEFORE ADJUDICATING": True, "key": key},
                   indent=2))
    print(f"wrote {len(manifest)} crops to {out_dir}, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
