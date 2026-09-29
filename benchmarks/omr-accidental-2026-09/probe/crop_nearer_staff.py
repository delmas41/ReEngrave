"""ROADMAP 2.7b — the print check for `belongs_to_a_nearer_staff`.

N heads the rule REFUSED and M heads it looked at and KEPT, from the arm
records (one or more `--arm LABEL=record.json=pdf`), shuffled together and
UNLABELLED which is which. Sean's five from the 2.7 adjudication are excluded:
they are already answered.

Each crop, cut from the PDF at the gather's own DPI (600):
  * the FILED staff's five lines drawn GREEN (the staff the record cut the
    head from), the NEAR staff's five lines drawn ORANGE (the other staff of
    the system nearest the head) — a crop between two staves commits to
    neither unless both are drawn (Sean, 2026-09-23);
  * the head bracketed BLUE on its exact `bbox_page_px`;
  * a spacing ruler on the left edge, ticks every staff space from the
    filed staff's top line.

⚠️ FRAME CONTROL, IMPORTED from `crop_inferred._frame_ok`: BOTH staves' own
`Q.STAFF_LINES` must be darker than a half-space off them on the render, or
the crop is REFUSED. `--break-frame` shifts every line half a space to watch
it refuse.

KEPT candidates, in order: heads past the distance band the rule kept
because a KEPT rung joins them to the filed staff (Sean's exception), then
heads just inside the band (filed 2.5-3.0 spaces, another staff nearer).

    python3 benchmarks/omr-accidental-2026-09/probe/crop_nearer_staff.py \\
        --arm litolff=<rec>=<pdf> --arm brahms=<rec>=<pdf> \\
        --refused 12 --kept 4 --out-dir <...>/out/print [--break-frame]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.record_io import load_record  # noqa: E402

_CI = ROOT / "benchmarks/omr-infer-duration-print-2026-09/probe/crop_inferred.py"
_spec = importlib.util.spec_from_file_location("crop_inferred", _CI)
crop_inferred = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crop_inferred)

ALREADY_ADJUDICATED = {"glyph/3/0/8/2/3", "glyph/3/0/8/6/12", "glyph/3/0/9/2/6",
                       "glyph/3/0/9/6/8", "glyph/3/0/9/7/5", "glyph/3/0/8/7/1"}


def _band(y, lines, sp):
    top, bot = min(lines), max(lines)
    if top <= y <= bot:
        return 0.0
    return ((top - y) if y < top else (y - bot)) / sp


def _candidates(label, path):
    rec = load_record(path)["record"]
    lines, spacing, box = {}, {}, {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "staff_lines":
            lines[o["subject"]] = [float(v) for v in o["value"]]
        elif q == "staff_spacing":
            spacing[o["subject"]] = float(o["value"])
        elif q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                box[o["subject"]] = (o["value"][0], pb)
    sup = {v.get("supersedes") for v in rec["verdicts"] if v.get("supersedes")}
    refused, kept_rung, kept_band = [], [], []
    for v in rec["verdicts"]:
        if v["id"] in sup or v["quantity"] != "notehead_is_not_a_notehead":
            continue
        sub = v["subject"]
        if sub in ALREADY_ADJUDICATED or sub not in box:
            continue
        sig = (v.get("detail") or {}).get("nearer_staff_signal") or {}
        item = {"label": label, "subject": sub, "reason": v["reason"],
                "value": v["value"], "signal": sig}
        if v["value"] is True and v["reason"] == "belongs_to_a_nearer_staff":
            refused.append(item)
        elif v["value"] is False and sig.get("near_staff"):
            f, n = sig.get("filed_spaces", 0), sig.get("near_spaces", 99)
            if f > 3.0 and n <= 2.75 and n < f and \
                    sig.get("kept_rungs_toward_filed", 0) > 0:
                kept_rung.append(item)
            elif 2.5 < f <= 3.0 and n < f:
                kept_band.append(item)
    return {"lines": lines, "spacing": spacing, "box": box}, refused, \
        kept_rung, kept_band


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", action="append", required=True,
                    help="LABEL=record.json=pdf")
    ap.add_argument("--refused", type=int, default=12)
    ap.add_argument("--kept", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--seed", type=int, default=277)
    ap.add_argument("--prefix", default="2.7b-")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--break-frame", action="store_true")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.load_default(size=20)
    rng = random.Random(a.seed)

    docs, refused, kept_rung, kept_band, pdfs = {}, [], [], [], {}
    for spec in a.arm:
        label, rec, pdf = spec.split("=", 2)
        docs[label], r, kr, kb = _candidates(label, rec)
        pdfs[label] = pdf
        print(f"{label}: refused {len(r)}, kept-by-rung {len(kr)}, "
              f"kept-in-band {len(kb)}")
        refused += r
        kept_rung += kr
        kept_band += kb
    # refused: spread over documents and pages — round-robin by (label, page)
    by_pg = {}
    for it in refused:
        by_pg.setdefault((it["label"], it["subject"].split("/")[1]), []).append(it)
    for v in by_pg.values():
        rng.shuffle(v)
    keys = sorted(by_pg)
    rng.shuffle(keys)
    pick_r = []
    while len(pick_r) < a.refused and any(by_pg.values()):
        for k in keys:
            if by_pg[k] and len(pick_r) < a.refused:
                pick_r.append(by_pg[k].pop())
    rng.shuffle(kept_rung)
    rng.shuffle(kept_band)
    pick_k = (kept_rung[: (a.kept + 1) // 2]
              + kept_band)[: a.kept]
    if len(pick_k) < a.kept:
        pick_k += kept_rung[(a.kept + 1) // 2:][: a.kept - len(pick_k)]
    jobs = [("refused", it) for it in pick_r] + [("kept", it) for it in pick_k]
    rng.shuffle(jobs)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = {}
    manifest, refused_crops = [], []
    for n, (kind, it) in enumerate(jobs, 1):
        D = docs[it["label"]]
        sub = it["subject"]
        _, p, s, st, c, _gi = sub.split("/")
        filed = f"staff/{p}/{s}/{st}"
        near = it["signal"].get("near_staff")
        key = (it["label"], int(p))
        if key not in pages:
            pm = fitz.open(pdfs[it["label"]])[int(p)].get_pixmap(dpi=a.dpi)
            im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples) \
                if pm.n >= 3 else Image.frombytes(
                    "L", (pm.width, pm.height), pm.samples).convert("RGB")
            pages[key] = (im, np.asarray(im.convert("L"), dtype=float))
        im, arr = pages[key]
        sp_f = D["spacing"][filed]
        lf = list(D["lines"][filed])
        ln = list(D["lines"].get(near, []))
        sp_n = D["spacing"].get(near, sp_f)
        if a.break_frame:
            lf = [y + sp_f / 2.0 for y in lf]
            ln = [y + sp_n / 2.0 for y in ln]
        ok_f, c_f = crop_inferred._frame_ok(arr, lf, sp_f)
        ok_n, c_n = crop_inferred._frame_ok(arr, ln, sp_n) if ln else (False, 0.0)
        if not (ok_f and ok_n):
            refused_crops.append({"subject": sub, "label": it["label"],
                                  "why": "FRAME CONTROL FAILED",
                                  "contrast_filed": round(c_f, 2),
                                  "contrast_near": round(c_n, 2)})
            continue
        cls, hb = D["box"][sub]
        ys = [hb[1], hb[3], min(lf), max(lf), min(ln), max(ln)]
        pad = 10.0 * sp_f
        cx0 = int(max(0, hb[0] - pad))
        cx1 = int(min(im.width, hb[2] + pad))
        cy0 = int(max(0, min(ys) - 1.5 * sp_f))
        cy1 = int(min(im.height, max(ys) + 1.5 * sp_f))
        Z = 2
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        # ⚠️ Sean, 2026-09-28: 2-px coloured lines were unreadable. Each
        # staff is a TRANSLUCENT BAND with thick lines and a large boxed
        # label inside it (the o26b style, `crop_losers_2_6b.make_crop`).
        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        big = ImageFont.load_default(size=max(28, int(sp_f * Z * 0.8)))
        for lines_, rgb, label in ((lf, (0, 160, 60), "GREEN - filed here"),
                                   (ln, (240, 130, 0), "ORANGE - nearest other")):
            if not lines_:
                continue
            top, bot = (min(lines_) - cy0) * Z, (max(lines_) - cy0) * Z
            od.rectangle([0, top, crop.width, bot], fill=rgb + (60,))
            for ly in lines_:
                od.line([(0, (ly - cy0) * Z), (crop.width, (ly - cy0) * Z)],
                        fill=rgb + (230,), width=5)
            ty = max(0, top + (bot - top) / 2 - big.size / 2)
            tw = od.textlength(label, font=big)
            od.rectangle([30, ty - 4, 30 + tw + 12, ty + big.size + 6],
                         fill=(255, 255, 255, 235), outline=rgb + (255,),
                         width=4)
            od.text((36, ty), label, fill=rgb + (255,), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        dr = ImageDraw.Draw(crop)
        y, k = (min(lf) - cy0) * Z, 0
        step = sp_f * Z
        while y > 0:
            y -= step
        while y < crop.height:
            dr.line([(2, y), (16, y)], fill=(0, 90, 200), width=2)
            y += step
        bx0, by0 = (hb[0] - cx0) * Z, (hb[1] - cy0) * Z
        bx1, by1 = (hb[2] - cx0) * Z, (hb[3] - cy0) * Z
        arm = max(8, int((bx1 - bx0) * 0.35))
        for (x, yy, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(x, yy), (x + dx * arm, yy)], fill=(0, 60, 230), width=7)
            dr.line([(x, yy), (x, yy + dy * arm)], fill=(0, 60, 230), width=7)
        band_h = 112
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        name = f"{a.prefix}{n:02d}"
        cd.text((6, 4), f"{name}  {it['label']}  pdf idx {p}, sys {int(s) + 1},"
                        f" cell {c}", fill=(0, 0, 0), font=font)
        cd.text((6, 30), f"GREEN = staff {st}: the head was FILED here",
                fill=(0, 110, 40), font=font)
        cd.text((6, 56), f"ORANGE = staff {near.split('/')[3]}: nearest "
                         f"other staff", fill=(200, 100, 0), font=font)
        cd.text((6, 82), f"BLUE = the head ({cls}): GREEN, ORANGE, or not "
                         f"a note?", fill=(0, 40, 160), font=font)
        out_im.save(out_dir / f"{name}.png")
        manifest.append({
            "file": f"{name}.png",
            "question": ("Which staff does the BLUE notehead belong to: the "
                         "GREEN (filed) staff, the ORANGE (nearest other) "
                         "staff, or is it not a note?"),
            "document": it["label"], "notehead": sub, "detector_class": cls,
            "filed_staff": filed, "near_staff": near,
            "head_page_box": [round(x, 1) for x in hb],
            "frame_contrast": {"filed": round(c_f, 2), "near": round(c_n, 2)},
            # ⚠️ THE KEY. Read only after adjudicating the crops.
            "reading": {"kind": kind, "reason": it["reason"],
                        "signal": it["signal"]},
            "VERDICT_none_yet": None,
        })
    Path(out_dir / f"{a.prefix}crop-manifest.json").write_text(json.dumps({
        "question": "belongs_to_a_nearer_staff (ROADMAP 2.7b)",
        "refused_requested": a.refused, "kept_requested": a.kept,
        "seed": a.seed, "dpi": a.dpi, "arms": a.arm,
        "excluded_already_adjudicated": sorted(ALREADY_ADJUDICATED),
        "crops": manifest, "refused": refused_crops}, indent=2))
    print(f"wrote {len(manifest)} crops, refused {len(refused_crops)}")
    for r in refused_crops[:5]:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
