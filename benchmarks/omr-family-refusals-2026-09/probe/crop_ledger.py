#!/usr/bin/env python3
"""ROADMAP 3.4g — crops of REFUSED and KEPT `ledgerLine` boxes, for Sean.

    python3 benchmarks/omr-family-refusals-2026-09/probe/crop_ledger.py \\
        --record <a shared record> --pdf <the plate> --label litolff-whole \\
        --out-dir benchmarks/omr-family-refusals-2026-09/out/print

Four crops per reason and four of the boxes the rule KEEPS, cut from the PDF
at the GATHER'S OWN DPI (read from the record's provenance, never assumed),
behind a frame control that can fail, with:

  * GREEN horizontals — the five `Q.STAFF_LINES` of the staff the box is
    filed on, so the crop says WHICH staff it is about (Sean, 2026-09-23:
    *"there is a staff at the top and a staff at the bottom - i dont know
    which staff the cell is focussing on"*);
  * a RED CORNER BRACKET on the EXACT box — never a margin tick at its x;
  * BLUE dashes at the RUNG STEPS this staff's convention allows, one and two
    spaces beyond each outer line, so *at a rung or not* is visible rather
    than asserted;
  * the reason, the staff step and the line gap in the caption and the
    sidecar.

⚠️ THE VERDICTS ARE THE DECISION'S OWN, RUN HERE, NOT A SECOND COPY OF ITS
RULE. This builds a Log holding only the rows `adjudicate_ledger_is_not_a_
ledger` DECLARES (`wants=` on the spec, asserted below so a widened
declaration fails loudly instead of being silently starved) and runs that one
decision over it. Re-deriving `on_a_staff_line` here would make the crops a
picture of this file's arithmetic.

⚠️ `_frame_ok` IS IMPORTED FROM `omr-infer-duration-print-2026-09/probe/
crop_inferred.py`, not copied. A crop whose frame control is a second copy of
somebody else's is a crop whose control has not been run.

⚠️ IT WRITES TO `out/print/`, NOT `out/crops/` — `.gitignore` excludes
`benchmarks/**/crops/` and these are the artefact.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))

from crop_inferred import _frame_ok                              # noqa: E402
from tools.omr.staged import adjudicate                          # noqa: E402
from tools.omr.staged import adjudicators                        # noqa: E402,F401
from tools.omr.staged.adjudicators import family_precision as FP  # noqa: E402
from tools.omr.staged.record import Log, Q, Subject, Kind        # noqa: E402
from tools.omr.staged.record_io import load_record               # noqa: E402

LEDGER = "ledgerLine"
#: The rows the decision declares. ⚠️ ASSERTED against the registry below.
NEEDED = (Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING, Q.CELL_STAFF_SPACE,
          Q.HUMAN_BOX_VERDICT)


def build(rec: dict):
    """A Log holding only the ledger decision's declared inputs."""
    spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
    missing = [w for w in spec.wants if w not in NEEDED]
    if missing:
        raise SystemExit(
            f"the decision now declares {missing}, which this probe does not "
            f"put in the Log — every crop would be starved of a row the real "
            f"run has. Add it here rather than letting the verdicts drift.")
    log = Log()
    idx = {}
    for o in rec["observations"]:
        q = o.get("quantity")
        if q not in NEEDED:
            continue
        v = o.get("value")
        if q == Q.GLYPH_BOX and not (
                isinstance(v, (list, tuple)) and len(v) == 5
                and v[0] == LEDGER):
            continue
        sub = Subject.from_key(o["subject"])
        detail = dict(o.get("detail") or {})
        log.observe(sub, q, v, reader=o["reader"], frame=o["frame"],
                    score=o.get("score"), **detail)
        idx[(q, o["subject"])] = v
        if q == Q.GLYPH_BOX:
            idx[("page_box", o["subject"])] = detail.get("bbox_page_px")
    log.freeze()
    adjudicate.run(log, order=(Q.LEDGER_IS_NOT_A_LEDGER,))
    return log, idx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dpi", type=int, default=None,
                    help="default: the record's own provenance")
    ap.add_argument("--per-reason", type=int, default=4)
    ap.add_argument("--pad-spaces", type=float, default=7.0)
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-family-refusals-2026-09/out/print")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.record)
    rec = d["record"]
    dpi = a.dpi or (((d.get("provenance") or {}).get("settings") or {})
                    .get("args", {}) or {}).get("dpi")
    if not dpi:
        raise SystemExit("no DPI in the record's provenance and none given — "
                         "a crop at the wrong DPI is a picture of a "
                         "different page")
    log, idx = build(rec)

    # ── group the verdicts by reason, and the HELD-BACK signal beside them ──
    by_reason: dict = {}
    for v in log.to_json()["verdicts"]:
        if v["quantity"] != Q.LEDGER_IS_NOT_A_LEDGER:
            continue
        det = v.get("detail") or {}
        if v["outcome"] != "decided":
            key = f"ABSTAINED:{v.get('reason')}"
        elif v["value"] is True:
            key = v.get("reason")
        elif (det.get("rung_step_signal") or {}).get("would_fire"):
            # ⚠️ THE HELD-BACK RULE GETS CROPS TOO, and they are the whole
            # point of holding it back: these are the boxes it WOULD refuse
            # and the shipped rules do not. Sean adjudicates them against the
            # print and that is what says whether the uniform offset
            # distribution is the page or the staff-line model.
            key = "not_at_a_rung_step_WOULD_FIRE_held_back"
        else:
            key = "kept"
        by_reason.setdefault(key, []).append(v)

    print("population by reason:",
          {k: len(v) for k, v in sorted(by_reason.items())})

    rng = random.Random(20260923)
    jobs = []
    for reason, vs in sorted(by_reason.items()):
        if reason.startswith("ABSTAINED"):
            continue
        rng.shuffle(vs)
        jobs += [(reason, v) for v in vs[:a.per_reason]]
    if not jobs:
        print("DEAD AT ZERO — no ledger verdict to crop.")
        return 2

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames, manifest, refused = {}, {}, [], []

    for reason, v in jobs:
        subj = v["subject"]
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
            pm = doc[p].get_pixmap(dpi=dpi)
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
        crop = im.crop((cx0, cy0, cx1, cy1))
        Z = 4
        crop = crop.resize(((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        # the staff's own five lines
        for ly in lines:
            y = (float(ly) - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)

        # the RUNG STEPS the convention allows, one and two spaces out
        top, bottom = min(float(t) for t in lines), max(float(t) for t in lines)
        for k in (1, 2, 3):
            for ry in (bottom + k * float(spacing), top - k * float(spacing)):
                y = (ry - cy0) * Z
                if 0 <= y < crop.height:
                    for x in range(0, crop.width, 24):
                        dr.line([(x, y), (x + 12, y)], fill=(40, 90, 220),
                                width=1)

        # a corner bracket on the EXACT box
        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        arm = max(6, int((bx1 - bx0) * 0.3))
        R, W = (220, 0, 0), 2
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm, ay)], fill=R, width=W)
            dr.line([(ax, ay), (ax, ay + dy * arm)], fill=R, width=W)

        det = v.get("detail") or {}
        band_h = 70
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        cd.text((6, 4), f"{subj}", fill=(0, 0, 0))
        cd.text((6, 20), f"VERDICT {reason}"
                         f"   (True = refused, this box is not a ledger line)",
                fill=(140, 0, 0))
        cd.text((6, 36), f"staff step {det.get('staff_step')}"
                         f"   gap to nearest staff LINE "
                         f"{det.get('line_gap_spaces')} spaces"
                         f"   beyond the band {det.get('beyond_the_band_spaces')}",
                fill=(0, 0, 0))
        cd.text((6, 52), "GREEN = this staff's 5 lines   BLUE dashes = the "
                         "rung steps the convention allows",
                fill=(0, 120, 45))
        crop = out_im

        name = f"{a.label}-p{p}-s{sy}-st{st}-c{ce}-g{gi}-{reason}.png"
        crop.save(out_dir / name)
        manifest.append({
            "file": name, "subject": subj, "reason": reason,
            "refused": v["value"] is True,
            "staff_step": det.get("staff_step"),
            "line_gap_spaces": det.get("line_gap_spaces"),
            "beyond_the_band_spaces": det.get("beyond_the_band_spaces"),
            "height_spaces": det.get("height_spaces"),
            "aspect_h_over_w": det.get("aspect_h_over_w"),
            "rung_step_signal": det.get("rung_step_signal"),
            "page": p, "system": sy, "staff": st, "cell": ce,
            "frame_contrast": round(contrast, 2),
            "page_box": [round(px0, 1), round(py0, 1),
                         round(px1, 1), round(py1, 1)],
            "dpi": dpi,
            "VERDICT_none_yet": None,
        })

    (out_dir / f"crop-manifest-{a.label}.json").write_text(json.dumps(
        {"record": Path(a.record).name, "dpi": dpi,
         "constants": {
             "ON_A_STAFF_LINE_TOL_SPACES": FP.ON_A_STAFF_LINE_TOL_SPACES,
             "TALL_MIN_HEIGHT_SPACES": FP.TALL_MIN_HEIGHT_SPACES,
             "RUNG_STEP_TOL_SPACES": FP.RUNG_STEP_TOL_SPACES,
             "RUNG_STEP_SHIPS": FP.RUNG_STEP_SHIPS},
         "population_by_reason": {k: len(v) for k, v in
                                  sorted(by_reason.items())},
         "crops": manifest, "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
