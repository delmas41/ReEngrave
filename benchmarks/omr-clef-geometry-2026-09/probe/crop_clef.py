#!/usr/bin/env python3
"""ROADMAP 2.11 — one header crop per NEWLY-READ clef, for Sean.

    python3 benchmarks/omr-clef-geometry-2026-09/probe/crop_clef.py \
        --arm <out>/arm-litolff-p3.record.json \
        --base <out>/base-litolff-p3.record.json \
        --pdf <the plate> --label litolff-p3 \
        --out-dir benchmarks/omr-clef-geometry-2026-09/out/print

A crop is cut from the PDF at the GATHER'S OWN DPI (read from the record's
`provenance.settings.args.dpi`, never assumed), behind a frame control that
can fail, with:

  * GREEN horizontals — the five `Q.STAFF_LINES` the clef is FILED on, so the
    crop says WHICH staff it is about (Sean's own correction of 2026-09-23:
    *"there is a staff at the top and a staff at the bottom - i dont know
    which staff the cell is focussing on"*);
  * BLUE box — the ink CLUSTER the locator read as a clef;
  * RED boxes — the notehead boxes the read OVERRODE, by name from the row;
  * the read family in the caption and in the `.json` sidecar.

⚠️ `_frame_ok` AND `_index` ARE IMPORTED FROM
`omr-infer-duration-print-2026-09/probe/crop_inferred.py`, not copied. A crop
whose frame control is a second copy of somebody else's is a crop whose
control has not been run.

⚠️ THE CLUSTER BOX IS DRAWN ONLY FOR A `cell:0`-FRAME READ, AND THE SIDECAR
SAYS SO WHEN IT IS NOT. `Q.CLEF_LOCATED.bbox` is in ITS OWN crop's canonical
pixels; the record carries `Q.CELL_BOX` + `Q.CELL_STAFF_SPACE` for cell 0 and
nothing at all for the header-window crop, so a header-frame bbox has no
exact route to page pixels. Declined rather than approximated — an
approximate box drawn on a plate for a human to adjudicate is worse than no
box (CLAUDE.md §6b: *the SUBJECT marked, a corner bracket on the exact head,
not a margin tick at its x*).

⚠️ IT WRITES TO `out/print/`, NOT `out/crops/` — `.gitignore` excludes
`benchmarks/**/crops/` and these are the artefact.
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


def _clef_verdicts(rec) -> Dict[str, dict]:
    return {v["subject"]: v for v in rec["verdicts"] if v["quantity"] == "clef"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--base", default=None,
                    help="if given, crop ONLY staves whose clef the arm reads "
                         "and the base did not")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--label", required=True)
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
    arm_clef = _clef_verdicts(rec)

    newly: Optional[set] = None
    if a.base:
        b = load_record(a.base)["record"]
        base_clef = _clef_verdicts(b)
        newly = {
            s for s, v in arm_clef.items()
            if v["outcome"] == "decided" and v.get("value") is not None
            and not (base_clef.get(s, {}).get("outcome") == "decided"
                     and base_clef.get(s, {}).get("value") is not None)
        }

    # ⚠️ THE DPI IS THE GATHER'S OWN, read off the record. A crop cut at a
    # different DPI from the one the boxes were measured at is a crop whose
    # rectangles are in the wrong place, and it looks exactly like a reading
    # error.
    prov = d.get("provenance") or {}
    dpi = int(((prov.get("settings") or {}).get("args") or {}).get("dpi") or 600)

    jobs: List[dict] = []
    for o in rec["observations"]:
        if o["quantity"] != "clef_located":
            continue
        det = o.get("detail") or {}
        if not det.get("overrides_notehead_box"):
            continue
        if newly is not None and o["subject"] not in newly:
            continue
        jobs.append(o)
    print("%d overriding clef reads to crop (dpi %d)" % (len(jobs), dpi))

    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(a.pdf)
    pages: Dict[int, Any] = {}
    frames: Dict[int, Any] = {}
    manifest: List[dict] = []
    refused: List[dict] = []

    for o in jobs:
        staff = o["subject"]
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

        scale = float(spacing) / float(css)      # canonical cell -> page px

        def to_page(box):
            gx, gy, gw, gh = box
            x0 = cbox[0] + gx * scale
            y0 = cbox[1] + gy * scale
            return [x0, y0, x0 + gw * scale, y0 + gh * scale]

        det = o.get("detail") or {}
        cluster_page = None
        cluster_note = ("bbox is in the header crop's own canonical frame and "
                        "the record carries no spacing for it — DECLINED, not "
                        "approximated")
        if o.get("frame") == "cell:0" and det.get("bbox"):
            cluster_page = to_page(det["bbox"])
            cluster_note = "exact: cell:0 canonical -> page via CELL_BOX"

        overrode = list(det.get("overrode_glyph_subjects") or ())
        boxes_page = []
        for g in overrode:
            gb = idx.get(("glyph_box", g))
            if not gb:
                continue
            boxes_page.append({"glyph": g, "class": str(gb[0]),
                               "page_px": to_page(gb[1:5])})

        # the crop window: the staff band, padded, around the header
        pad = a.pad_spaces * float(spacing)
        xs = [cbox[0]] + [b["page_px"][2] for b in boxes_page]
        if cluster_page:
            xs.append(cluster_page[2])
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

        for y in lines:                                   # GREEN: the staff
            yy = (y - y0) * zoom
            dr.line([(0, yy), (crop.width, yy)], fill=(0, 170, 0), width=2)
        if cluster_page:                                  # BLUE: the cluster
            R(cluster_page, (0, 90, 255), 4)
        for b in boxes_page:                              # RED: the overrides
            R(b["page_px"], (230, 0, 0), 3)

        # ⚠️ THE FRAME IS IN THE FILENAME. A staff produces up to TWO
        # overriding reads — the header crop and cell 0 — and naming them
        # alike made the second silently overwrite the first, which is a crop
        # pass quietly losing half its evidence.
        name = "%s-s%d-st%d-%s-%s.png" % (
            a.label, sy, st, o.get("value"),
            str(o.get("frame", "?")).replace(":", ""))
        (out_dir / name).parent.mkdir(parents=True, exist_ok=True)
        crop.save(out_dir / name)
        side = {
            "png": name,
            "caption": ("%s system %d staff %d — READ %s by geometry over %d "
                        "notehead box(es). GREEN = the staff's five "
                        "Q.STAFF_LINES; BLUE = the ink cluster read as the "
                        "clef; RED = the detector notehead boxes the read "
                        "overrode and the exporter now refuses `is_a_clef`."
                        % (a.label, sy, st, o.get("value"), len(boxes_page))),
            "staff": staff, "page": p, "dpi": dpi, "zoom": zoom,
            "frame_control": {"passed": True, "contrast": round(contrast, 2)},
            "read": {"clef": o.get("value"), "frame": o.get("frame"),
                     "symmetry": o.get("score"),
                     "h_spaces": det.get("h_spaces"),
                     "w_spaces": det.get("w_spaces")},
            "cluster_page_px": cluster_page,
            "cluster_note": cluster_note,
            "overrode": boxes_page,
            "staff_lines_page_px": list(lines),
            "crop_page_px": [x0, y0, x1, y1],
            "VERDICT_none_yet": None,
        }
        (out_dir / (name[:-4] + ".json")).write_text(json.dumps(side, indent=1))
        manifest.append(side)
        print("  %s  (%s, symmetry %s, %d overridden)"
              % (name, o.get("value"), o.get("score"), len(boxes_page)))

    (out_dir / ("MANIFEST-%s.json" % a.label)).write_text(json.dumps(
        {"label": a.label, "dpi": dpi, "crops": manifest, "refused": refused,
         "VERDICT_none_yet": None,
         "_readme": "One crop per clef this arm reads over a notehead box. "
                    "`VERDICT_none_yet` is null on every crop and on this "
                    "manifest until Sean adjudicates them against the print; "
                    "nothing in ROADMAP 2.11 has been print-confirmed."},
        indent=1))
    print("refused: %s" % refused)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
