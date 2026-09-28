#!/usr/bin/env python3
"""ROADMAP 3.4g-2 — crops of what Sean's two ledger conventions CHANGE.

    python3 benchmarks/omr-family-refusals-2026-09/probe/crop_ledger_g2.py \\
        --record <library>/_shared-records/beethoven5-p1-p4.record.json \\
        --pdf <the Litolff plate> --label g2-litolff-p1p4 --dpi 600

Picks, from the SAME record Sean's thirteen crops came from:
  * 4 boxes 3.4g KEPT and 3.4g-2 refuses `inside_the_staff`;
  * 4 boxes 3.4g KEPT and 3.4g-2 refuses `no_head_on_the_rung`;
  * 4 boxes both rules KEEP;
  * the two real rungs the old rules refused or would have (Sean's crops 3
    and 9), which must now be KEPT.

Everything `crop_ledger.py` draws (the staff's own five lines in GREEN, the
rung steps in BLUE dashes, a RED corner bracket on the exact box), plus every
notehead box that x-overlaps the rung in ORANGE — the ink the head rule reads
— and the head facts in the caption.

⚠️ BOTH VERDICTS ARE THE DECISIONS' OWN, RUN HERE. The Log holds the rows
the decision declares — `Q.GLYPH_BOX` for `ledgerLine` AND `notehead*`
boxes, since 3.4g-2 reads the heads — and the BASE is 3.4g's function loaded
from `origin/main` exactly as `readjudicate_ledger_g2.py` loads it.

⚠️ `_frame_ok` IS IMPORTED, not copied (`omr-infer-duration-print-2026-09/
probe/crop_inferred.py`), and it writes to `out/print/`, never `out/crops/`.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import random
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crop_inferred import _frame_ok                              # noqa: E402
from readjudicate_ledger_g2 import load_base_fn                  # noqa: E402
from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.adjudicators import family_precision as FP  # noqa: E402
from tools.omr.staged.record import Log, Q, Subject, Kind        # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402

LEDGER = "ledgerLine"
NEEDED = (Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.CELL_STAFF_SPACE,
          Q.HUMAN_BOX_VERDICT, Q.GLYPH_BAND_DISTANCE)
#: Sean's crops 3 and 9, the two real rungs 3.4g refused or would have.
RESCUED = ("glyph/4/1/7/5/21", "glyph/4/1/2/5/14")


def build(rec: dict):
    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    missing = [w for w in spec.wants if w not in NEEDED]
    if missing:
        raise SystemExit(f"the decision now declares {missing}; add it here")
    log, idx, heads = Log(), {}, {}
    for o in rec["observations"]:
        q = o.get("quantity")
        if q not in NEEDED:
            continue
        v = o.get("value")
        if q == Q.GLYPH_BOX:
            if not (isinstance(v, (list, tuple)) and len(v) == 5):
                continue
            is_head = FP._is_notehead_class(v[0])
            if v[0] != LEDGER and not is_head:
                continue
        sub = Subject.from_key(o["subject"])
        detail = dict(o.get("detail") or {})
        log.observe(sub, q, v, reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **detail)
        idx[(q, o["subject"])] = v
        if q == Q.GLYPH_BOX:
            idx[("page_box", o["subject"])] = detail.get("bbox_page_px")
            if v[0] != LEDGER:
                heads.setdefault(sub.at(Kind.CELL).to_key(), []).append(
                    (v, detail.get("bbox_page_px")))
    log.freeze()
    return log, idx, heads


def decide(log: Log, fn=None):
    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    if fn is not None:
        adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = dataclasses.replace(
            spec, fn=fn)
    try:
        return {v.subject.to_key(): v
                for v in adjudicate.run(log, order=(Q.LEDGER_IS_NOT_A_LEDGER,))}
    finally:
        adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = spec


def word(v) -> str:
    if v.outcome.value != "decided":
        return f"ABSTAINED:{v.reason}"
    return v.reason if v.value is True else "kept"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dpi", type=int, required=True)
    ap.add_argument("--per-bucket", type=int, default=4)
    ap.add_argument("--pad-spaces", type=float, default=7.0)
    ap.add_argument("--base-ref", default="origin/main")
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-family-refusals-2026-09/out/print")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    rec = load_record(a.record)["record"]
    # ⚠️ TWO LOGS: a frozen log records one verdict per subject and quantity,
    # so the base and the arm cannot share one.
    log_b, idx, heads = build(rec)
    log_a, _i, _h = build(rec)
    base = decide(log_b, load_base_fn(a.base_ref))
    arm = decide(log_a)

    buckets = {"kept_to_inside_the_staff": [], "kept_to_no_head_on_the_rung": [],
               "kept_both": [], "rescued": []}
    for key, va in arm.items():
        b, w = word(base[key]), word(va)
        if key in RESCUED:
            buckets["rescued"].append(key)
        elif b == "kept" and w == "inside_the_staff":
            buckets["kept_to_inside_the_staff"].append(key)
        elif b == "kept" and w == "no_head_on_the_rung":
            buckets["kept_to_no_head_on_the_rung"].append(key)
        elif b == "kept" and w == "kept":
            buckets["kept_both"].append(key)
    print("population:", {k: len(v) for k, v in buckets.items()})
    rng = random.Random(20260927)
    jobs = []
    for name, keys in buckets.items():
        keys = sorted(keys)
        rng.shuffle(keys)
        # ⚠️ ONE EXTRA per bucket so a frame-control refusal still leaves the
        # asked-for number; the extras are cut only if a sibling is refused.
        jobs += [(name, k, i >= a.per_bucket) for i, k in
                 enumerate(keys if name == "rescued"
                           else keys[:a.per_bucket + 2])]
    if not jobs:
        print("DEAD AT ZERO")
        return 2

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames, manifest, refused = {}, {}, [], []
    written = {k: 0 for k in buckets}

    for bucket, subj, spare in jobs:
        if spare and written[bucket] >= a.per_bucket:
            continue
        sub = Subject.from_key(subj)
        p, sy, st, ce, gi = sub.page, sub.system, sub.staff, sub.cell, sub.glyph
        staff = sub.at(Kind.STAFF).to_key()
        lines = idx.get((Q.STAFF_LINES, staff))
        spacing = idx.get((Q.STAFF_SPACING, staff))
        box = idx.get(("page_box", subj))
        if not (lines and spacing and box):
            refused.append({"subject": subj, "why": "geometry missing"})
            continue
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=a.dpi)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        im, arr = pages[p], frames[p]
        ok, contrast = _frame_ok(arr, lines, spacing)
        if not ok:
            refused.append({"subject": subj, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        px0, py0, px1, py1 = [float(t) for t in box]
        pad = a.pad_spaces * float(spacing)
        cx0, cy0 = int(max(0, px0 - pad)), int(max(0, py0 - pad))
        cx1 = int(min(im.width, px1 + pad))
        cy1 = int(min(im.height, py1 + pad))
        Z = 4
        crop = im.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)
        for ly in lines:
            y = (float(ly) - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)
        top, bottom = min(float(t) for t in lines), max(float(t) for t in lines)
        for k in (1, 2, 3):
            for ry in (bottom + k * float(spacing), top - k * float(spacing)):
                y = (ry - cy0) * Z
                if 0 <= y < crop.height:
                    for x in range(0, crop.width, 24):
                        dr.line([(x, y), (x + 12, y)], fill=(40, 90, 220),
                                width=1)
        # the heads the rule reads: x-overlapping, same cell, in ORANGE
        rung = idx[(Q.GLYPH_BOX, subj)]
        n_over = 0
        for hv, hb in heads.get(sub.at(Kind.CELL).to_key(), ()):
            if min(hv[1] + hv[3], rung[1] + rung[3]) - max(hv[1], rung[1]) <= 0:
                continue
            n_over += 1
            if hb:
                hx0, hy0, hx1, hy1 = [(float(t) - o) * Z for t, o in
                                      zip(hb, (cx0, cy0, cx0, cy0))]
                dr.rectangle([hx0, hy0, hx1, hy1], outline=(240, 140, 0),
                             width=2)
        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        armlen = max(6, int((bx1 - bx0) * 0.3))
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * armlen, ay)], fill=(220, 0, 0),
                    width=2)
            dr.line([(ax, ay), (ax, ay + dy * armlen)], fill=(220, 0, 0),
                    width=2)

        det = arm[subj].detail or {}
        band_h = 86
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"{subj}   staff {staff} (GREEN lines)", fill=(0, 0, 0))
        cd.text((6, 20), f"3.4g: {word(base[subj])}   ->   3.4g-2: "
                         f"{word(arm[subj])}", fill=(140, 0, 0))
        cd.text((6, 36), f"staff step {det.get('staff_step')}   beyond the "
                         f"band {det.get('beyond_the_band_spaces')} sp   "
                         f"height {det.get('height_spaces')} sp",
                fill=(0, 0, 0))
        cd.text((6, 52), f"heads x-overlapping {det.get('heads_x_overlapping')}"
                         f"   nearest {det.get('head_distance_spaces')} sp   "
                         f"farthest out {det.get('head_outward_spaces')} sp   "
                         f"on the box {det.get('head_on_the_box')}",
                fill=(0, 0, 0))
        cd.text((6, 68), "RED = the box   ORANGE = the heads the rule reads   "
                         "BLUE dashes = rung steps", fill=(0, 120, 45))
        fname = (f"g2-{a.label}-p{p}-s{sy}-st{st}-c{ce}-g{gi}-"
                 f"{bucket}.png")
        out_im.save(out_dir / fname)
        written[bucket] += 1
        manifest.append({
            "file": fname, "subject": subj, "staff": staff, "bucket": bucket,
            "verdict_3_4g": word(base[subj]),
            "verdict_3_4g_2": word(arm[subj]),
            "staff_step": det.get("staff_step"),
            "beyond_the_band_spaces": det.get("beyond_the_band_spaces"),
            "line_gap_spaces": det.get("line_gap_spaces"),
            "height_spaces": det.get("height_spaces"),
            "heads_x_overlapping": det.get("heads_x_overlapping"),
            "head_distance_spaces": det.get("head_distance_spaces"),
            "head_outward_spaces": det.get("head_outward_spaces"),
            "head_on_the_box": det.get("head_on_the_box"),
            "heads_drawn": n_over,
            "frame_contrast": round(contrast, 2),
            "page_box": [round(px0, 1), round(py0, 1),
                         round(px1, 1), round(py1, 1)],
            "dpi": a.dpi,
            "VERDICT_none_yet": None,
        })

    (out_dir / f"crop-manifest-g2-{a.label}.json").write_text(json.dumps(
        {"record": Path(a.record).name, "dpi": a.dpi, "base_ref": a.base_ref,
         "constants": {
             "ON_A_STAFF_LINE_TOL_SPACES": FP.ON_A_STAFF_LINE_TOL_SPACES,
             "TALL_MIN_HEIGHT_SPACES": FP.TALL_MIN_HEIGHT_SPACES,
             "HEAD_NEAR_TOL_SPACES": FP.HEAD_NEAR_TOL_SPACES,
             "RUNG_STEP_SHIPS": FP.RUNG_STEP_SHIPS},
         "population_by_bucket": {k: len(v) for k, v in buckets.items()},
         "written_by_bucket": written,
         "crops": manifest, "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops {written}, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
