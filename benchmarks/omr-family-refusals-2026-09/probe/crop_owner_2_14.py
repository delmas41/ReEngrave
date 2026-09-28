#!/usr/bin/env python3
"""ROADMAP 2.14 — crops of the `glyph_owner` verdicts the rung-naming
discount CHANGED.

    python3 benchmarks/omr-family-refusals-2026-09/probe/crop_owner_2_14.py \\
        --base <base.record.json> --arm <arm.record.json> --pdf <the plate> \\
        --label l214-litolff-p3

Reads the base/arm `Q.GLYPH_OWNER` verdicts straight off each record — both
are ADJUDICATE's own output, nothing here re-derives a verdict — finds the
subjects where they disagree, and for each (up to `--limit`) cuts a crop
from the PDF at the record's own DPI: the ARM'S OWN WINNING STAFF'S five
`Q.STAFF_LINES` in GREEN (`feedback_send_sean_the_crop.md`, 2026-09-23: a
crop that does not draw the staff it is filed on commits to neither and is
not evidence), a RED corner bracket on the EXACT glyph box, and the base and
arm verdicts, plus the discounted rung keys, in the caption.

⚠️ FRAME-CONTROLLED. `_frame_ok` (`omr-infer-duration-print-2026-09/probe/
crop_inferred.py`, imported not copied) checks the drawn staff lines are
actually darker than their surroundings at the record's own DPI; a crop
whose frame fails is refused rather than shown.

⚠️ WRITES TO `out/print/`, NOT `out/crops/` — `.gitignore` excludes
`benchmarks/**/crops/` and these are the artefact, with a JSON sidecar
carrying `VERDICT_none_yet: null` per crop for Sean.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))

from crop_inferred import _frame_ok                              # noqa: E402
from tools.omr.staged.record import Q, Subject, Kind             # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402


def _index(rec):
    out = {}
    for o in rec["observations"]:
        if o["quantity"] in (Q.GLYPH_BOX, Q.STAFF_LINES, Q.STAFF_SPACING):
            out.setdefault(o["quantity"], {})[o["subject"]] = o
    return out


def _owner_verdicts(rec):
    return {v["subject"]: v for v in rec["verdicts"]
            if v["quantity"] == Q.GLYPH_OWNER}


def _word(v):
    if v is None:
        return "<absent>"
    val = v.get("value")
    return val if val is not None else f"ABSTAINED:{v.get('reason')}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--pad-spaces", type=float, default=7.0)
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-family-refusals-2026-09/out/print")
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    B = load_record(a.base)
    A = load_record(a.arm)
    rb, ra = B["record"], A["record"]
    dpi = (((A.get("provenance") or {}).get("settings") or {})
           .get("args", {}) or {}).get("dpi")
    if not dpi:
        raise SystemExit("no DPI in the arm's provenance -- a crop at the "
                         "wrong DPI is a picture of a different page")

    ib, ia = _index(rb), _index(ra)
    vb, va = _owner_verdicts(rb), _owner_verdicts(ra)

    changed = [(subj, vb.get(subj), va.get(subj))
              for subj in sorted(set(vb) | set(va))
              if _word(vb.get(subj)) != _word(va.get(subj))]
    print(f"glyph_owner verdicts changed: {len(changed)}")
    if not changed:
        print("DEAD AT ZERO -- no changed ownership verdict to crop.")
        return 2

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages, frames, manifest, refused = {}, {}, [], []

    for subj, wb, wa in changed[: a.limit]:
        sub = Subject.from_key(subj)
        p, sy, st, ce, gi = sub.page, sub.system, sub.staff, sub.cell, sub.glyph
        box_row = (ia.get(Q.GLYPH_BOX, {}).get(subj)
                  or ib.get(Q.GLYPH_BOX, {}).get(subj))
        if box_row is None:
            refused.append({"subject": subj, "why": "no GLYPH_BOX row"})
            continue
        page_box = (box_row.get("detail") or {}).get("bbox_page_px")
        winner = wa.get("value") if wa else None
        winner_staff = (Subject.from_key(winner) if winner
                        else sub.at(Kind.STAFF))
        lines_row = ia.get(Q.STAFF_LINES, {}).get(winner_staff.to_key())
        spacing_row = ia.get(Q.STAFF_SPACING, {}).get(winner_staff.to_key())
        if not (page_box and lines_row and spacing_row):
            refused.append({"subject": subj, "why": "geometry missing",
                            "winner_staff": winner_staff.to_key()})
            continue
        lines = lines_row["value"]
        spacing = spacing_row["value"]

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

        px0, py0, px1, py1 = [float(t) for t in page_box]
        pad = a.pad_spaces * float(spacing)
        cx0, cy0 = int(max(0, px0 - pad)), int(max(0, py0 - pad))
        cx1 = int(min(im.width, px1 + pad))
        cy1 = int(min(im.height, py1 + pad))
        crop = im.crop((cx0, cy0, cx1, cy1))
        Z = 4
        crop = crop.resize(((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        # the WINNING staff's own five lines, so the crop NAMES it
        for ly in lines:
            y = (float(ly) - cy0) * Z
            if 0 <= y < crop.height:
                dr.line([(0, y), (crop.width, y)], fill=(0, 160, 60), width=1)

        # a RED corner bracket on the EXACT box
        bx0, by0 = (px0 - cx0) * Z, (py0 - cy0) * Z
        bx1, by1 = (px1 - cx0) * Z, (py1 - cy0) * Z
        arm_len = max(6, int((bx1 - bx0) * 0.3))
        RED, W = (220, 0, 0), 2
        for (ax, ay, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax, ay), (ax + dx * arm_len, ay)], fill=RED, width=W)
            dr.line([(ax, ay), (ax, ay + dy * arm_len)], fill=RED, width=W)

        band_h = 86
        out_im = Image.new("RGB", (crop.width, crop.height + band_h), "white")
        out_im.paste(crop, (0, band_h))
        cd = ImageDraw.Draw(out_im)
        det_a = (wa.get("detail") or {}) if wa else {}
        discounted = det_a.get("ladder_discounted_rungs") or {}
        cd.text((6, 4),
                f"{subj}   staff filed on (ARM): {winner_staff.to_key()}",
                fill=(0, 0, 0))
        cd.text((6, 20),
                f"BASE {_word(wb)}   reason={wb.get('reason') if wb else None}",
                fill=(140, 0, 0))
        cd.text((6, 36),
                f"ARM  {_word(wa)}   reason={wa.get('reason') if wa else None}",
                fill=(0, 0, 150))
        cd.text((6, 52), f"discounted rungs: {json.dumps(discounted)}",
                fill=(0, 0, 0))
        cd.text((6, 68),
                "GREEN = the staff this verdict is filed on (ARM's winner)",
                fill=(0, 120, 45))
        crop = out_im

        name = f"{a.label}-p{p}-s{sy}-st{st}-c{ce}-g{gi}.png"
        crop.save(out_dir / name)
        manifest.append({
            "file": name, "subject": subj,
            "base_value": wb.get("value") if wb else None,
            "base_reason": wb.get("reason") if wb else None,
            "arm_value": wa.get("value") if wa else None,
            "arm_reason": wa.get("reason") if wa else None,
            "ladder_discounted_rungs": discounted,
            "page": p, "system": sy, "staff": st, "cell": ce,
            "frame_contrast": round(contrast, 2),
            "page_box": [round(px0, 1), round(py0, 1),
                        round(px1, 1), round(py1, 1)],
            "dpi": dpi,
            "VERDICT_none_yet": None,
        })

    (out_dir / f"crop-manifest-{a.label}.json").write_text(json.dumps(
        {"base": Path(a.base).name, "arm": Path(a.arm).name, "dpi": dpi,
         "changed_count": len(changed), "crops": manifest,
         "refused": refused}, indent=2))
    print(f"wrote {len(manifest)} crops, refused {len(refused)}")
    for r in refused:
        print("  REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
