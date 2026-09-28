#!/usr/bin/env python3
"""ROADMAP 2.11b — one header crop per CHANGED clef verdict, for Sean.

    python3 benchmarks/omr-clef-geometry-2026-09/probe/crop_offstaff.py \
        --arm <out>/arm-breitkopf.record.json \
        --pdf <the plate> --label c211b-breitkopf \
        --subject staff/6/1/3 \
        --out-dir benchmarks/omr-clef-geometry-2026-09/out/print

Adapted from this same lane's `crop_clef.py` (roadmap 2.11): same DPI
discipline (read off `provenance.settings.args.dpi`, never assumed), same
frame control (`crop_inferred._frame_ok`, imported not copied), same
GREEN-staff-lines convention (CLAUDE.md's own correction, 2026-09-23: a crop
must say WHICH staff it is about).

⚠️ WHAT DIFFERS FROM `crop_clef.py`: that script boxes a CV-LOCATOR cluster
(`Q.CLEF_LOCATED.bbox`, in the cell's own canonical frame). This one boxes
the DETECTOR's own clef glyph box (`Q.GLYPH_BOX`, cell 0 only — "a clef is
read at the head of the staff"), matched to the discounted or deciding
`Q.CLEF_GLYPH` row by an EXACT (x_canonical, y_canonical) match — both rows
come from the same `Detection` object in `gather_clefs`, so this is the same
value read twice, not a coincidence needing a tolerance (the same
justification `clef._human_clef_position`'s exact float match uses).
RED = a glyph box `clef.py` DISCOUNTED `clef_box_off_the_staff` this run;
BLUE = a glyph box that WON the contest (`used`, per the verdict).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))

from crop_inferred import _frame_ok, _index                    # noqa: E402
from tools.omr.staged.record_io import load_record             # noqa: E402
from tools.omr.staged.adjudicators import clef as C            # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--base", default=None,
                     help="if given, the caption also shows the base verdict")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--subject", action="append", required=True,
                     help="staff/<p>/<s>/<st>, repeatable")
    ap.add_argument("--out-dir",
                     default="benchmarks/omr-clef-geometry-2026-09/out/print")
    ap.add_argument("--pad-spaces", type=float, default=10.0)
    a = ap.parse_args()

    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(a.arm)
    rec = d["record"]
    idx = _index(rec)
    clef_v = {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "clef"}
    base_v: Dict[str, dict] = {}
    if a.base:
        b = load_record(a.base)["record"]
        base_v = {v["subject"]: v for v in b["verdicts"] if v["quantity"] == "clef"}

    obs_by_id = {o["id"]: o for o in rec["observations"]}

    prov = d.get("provenance") or {}
    dpi = int(((prov.get("settings") or {}).get("args") or {}).get("dpi") or 600)

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages: Dict[int, Any] = {}
    frames: Dict[int, Any] = {}
    manifest: List[dict] = []
    refused: List[dict] = []

    for staff in a.subject:
        _, p, sy, st = staff.split("/")
        p, sy, st = int(p), int(sy), int(st)
        cell = "cell/%d/%d/%d/0" % (p, sy, st)
        cbox = idx.get(("cell_box", cell))
        css = idx.get(("cell_staff_space", cell))
        lines = idx.get(("staff_lines", staff))
        spacing = idx.get(("staff_spacing", staff))
        if not all((cbox, css, lines, spacing)):
            refused.append({"staff": staff, "why": "geometry missing"})
            continue

        v = clef_v.get(staff, {})
        discounted = (v.get("detail") or {}).get(C.OFF_STAFF_REASON) or []
        discounted_glyph_ids = {e["glyph_row"] for e in discounted}
        used_ids = set(v.get("used") or ())

        # Every cell-0 glyph_box that is a clef class, matched by an EXACT
        # (x_canonical, y_canonical) hit against this staff's own
        # Q.CLEF_GLYPH rows -- the join `clef._on_staff_rows` performs by
        # y_center alone, tightened here with x too since we have it.
        clef_glyph_rows = [o for o in rec["observations"]
                           if o["subject"] == staff
                           and o["quantity"] == "clef_glyph"]
        glyph_boxes = [o for o in rec["observations"]
                       if o["quantity"] == "glyph_box"
                       and o["subject"].startswith("glyph/%d/%d/%d/0/" % (p, sy, st))]

        boxes_to_draw = []
        for cg in clef_glyph_rows:
            cgd = cg.get("detail") or {}
            yc, xc = cgd.get("y_center"), cgd.get("x_center")
            match = None
            for gb in glyph_boxes:
                gv = gb.get("value")
                if not isinstance(gv, (list, tuple)) or len(gv) != 5:
                    continue
                # ⚠️ `Q.GLYPH_BOX`'s (x, y) is the box's TOP-LEFT corner in
                # canonical units (`gather.py`: `d.x_canonical, d.y_canonical,
                # d.width_canonical, d.height_canonical`), while
                # `Q.CLEF_GLYPH`'s detail carries `x_center`/`y_center`
                # (`d.x_center, d.y_center`) -- the SAME detection `d`, two
                # different fields. Verified against the raw record
                # (`glyph/6/1/3/0/1` = clefG at (139, 842, 177, 55); centre
                # (227.5, 869.5) matches the clef row's (227, 869) exactly):
                # the corner form needs +w/2, +h/2 before it is the same
                # value the clef row already carries.
                gx, gy, gw, gh = (float(gv[1]), float(gv[2]),
                                  float(gv[3]), float(gv[4]))
                gcx, gcy = gx + gw / 2.0, gy + gh / 2.0
                if xc is not None and abs(gcx - float(xc)) < 1.0 \
                        and yc is not None and abs(gcy - float(yc)) < 1.0:
                    match = gv
                    break
            if match is None:
                continue
            colour = ((230, 0, 0) if cg["id"] in discounted_glyph_ids
                      else (0, 90, 255) if cg["id"] in used_ids
                      else (255, 165, 0))
            boxes_to_draw.append({
                "glyph_row": cg["id"], "class": match[0],
                "canonical_box": [match[1], match[2], match[3], match[4]],
                "colour": "RED (discounted)" if cg["id"] in discounted_glyph_ids
                          else "BLUE (used)" if cg["id"] in used_ids
                          else "ORANGE (present, neither used nor discounted)",
                "_rgb": colour,
            })

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
            refused.append({"staff": staff, "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        scale = float(spacing) / float(css)

        def to_page(box):
            gx, gy, gw, gh = box
            x0 = cbox[0] + gx * scale
            y0 = cbox[1] + gy * scale
            return [x0, y0, x0 + gw * scale, y0 + gh * scale]

        boxes_page = []
        for b in boxes_to_draw:
            pb = to_page(b["canonical_box"])
            boxes_page.append({**b, "page_px": pb})

        pad = a.pad_spaces * float(spacing)
        xs = [cbox[0]] + [b["page_px"][2] for b in boxes_page]
        x0 = max(0, cbox[0] - float(spacing))
        x1 = min(im.width, max(xs) + pad)
        y0 = max(0, min(lines) - pad)
        y1 = min(im.height, max(lines) + pad)

        crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
        zoom = 4
        crop = crop.resize((crop.width * zoom, crop.height * zoom),
                           Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        def R(b, colour, width=3):
            dr.rectangle([(b[0] - x0) * zoom, (b[1] - y0) * zoom,
                          (b[2] - x0) * zoom, (b[3] - y0) * zoom],
                         outline=colour, width=width)

        for y in lines:
            yy = (y - y0) * zoom
            dr.line([(0, yy), (crop.width, yy)], fill=(0, 170, 0), width=2)
        for b in boxes_page:
            R(b["page_px"], b["_rgb"], 4)

        # ⚠️ PAGE IS IN THE NAME. Unlike `crop_clef.py` (always called with
        # one page's own label), this script takes subjects spanning a whole
        # document in one call, and `staff/14/1/9` / `staff/6/1/9` collide on
        # (system, staff) alone -- caught by a real filename collision, not
        # reasoned out in advance.
        name = "%s-p%d-s%d-st%d-%s.png" % (a.label, p, sy, st,
                                            v.get("value") or "abstained")
        (out_dir / name).parent.mkdir(parents=True, exist_ok=True)
        crop.save(out_dir / name)
        side = {
            "png": name, "staff": staff, "page": p, "dpi": dpi, "zoom": zoom,
            "caption": ("%s system %d staff %d — arm clef %s/%s (base %s/%s). "
                        "GREEN = the staff's five Q.STAFF_LINES; RED = a "
                        "detector clef box DISCOUNTED clef_box_off_the_staff; "
                        "BLUE = the box the winning verdict USED; ORANGE = "
                        "present but neither."
                        % (a.label, sy, st, v.get("outcome"), v.get("value"),
                           base_v.get(staff, {}).get("outcome"),
                           base_v.get(staff, {}).get("value"))),
            "frame_control": {"passed": True, "contrast": round(contrast, 2)},
            "arm_verdict": {"outcome": v.get("outcome"), "value": v.get("value"),
                            "reason": v.get("reason"), "decider": v.get("decider")},
            "base_verdict": base_v.get(staff),
            "boxes": [{"glyph_row": b["glyph_row"], "class": b["class"],
                       "colour": b["colour"], "page_px": b["page_px"]}
                      for b in boxes_page],
            "staff_lines_page_px": list(lines),
            "crop_page_px": [x0, y0, x1, y1],
            "VERDICT_none_yet": None,
        }
        (out_dir / (name[:-4] + ".json")).write_text(json.dumps(side, indent=1))
        manifest.append(side)
        print("  %s  (%d boxes drawn)" % (name, len(boxes_page)))

    (out_dir / ("MANIFEST-%s.json" % a.label)).write_text(json.dumps(
        {"label": a.label, "dpi": dpi, "crops": manifest, "refused": refused,
         "VERDICT_none_yet": None,
         "_readme": "One crop per CHANGED clef verdict, roadmap 2.11b. "
                    "`VERDICT_none_yet` is null on every crop and on this "
                    "manifest until Sean adjudicates them against the print."},
        indent=1))
    print("refused:", refused)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
