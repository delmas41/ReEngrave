#!/usr/bin/env python3
"""Is a `rest*` box's ink a filled ELLIPSE, not a rest? — ROADMAP 3.4g-4 Part B.

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: a rest glyph is
never a filled ellipse; a box whose ink is a filled, roughly elliptical blob
about one staff-space tall is a NOTEHEAD, not a rest. Sean has confirmed only
ONE instance: `glyph/3/1/4/8/8` on the Litolff count page (`benchmarks/
omr-shape-role-2026-09/out/print/ADJUDICATION-sean-2026-09-27-cal.json`,
crop 5 — "a quarter note head — NOT a rest"). NOT CONFIRMED on any other row.

    python3 benchmarks/omr-family-refusals-2026-09/probe/rest_round_ink.py \\
        --out benchmarks/omr-family-refusals-2026-09/out/r34g4-round-ink.json

Over every `rest*` `Q.GLYPH_BOX` on the two scan count pages (Litolff pdf
index 3, Breitkopf pdf index 1 — CLAUDE.md Sec.6a), this measures two cheap
ink-shape features from the raster AT THE GATHER'S OWN DPI (read off
`provenance.settings.args.dpi`, exactly as `crop_rest_slot.py` does):

  fill_ratio               ink pixels / box area, inside the DETECTOR's own
                           box (Otsu per crop, so a bitonal and a grayscale
                           plate are read by the same rule)
  largest_fill_ratio       the largest connected ink component's own pixel
                           count / ITS OWN tight bounding box area — an
                           ellipse inscribed in its bounding box fills
                           pi/4 = 0.785 of it; a rest's stroke (a rectangle
                           for whole/half, a thin hooked stroke for
                           quarter/8th/16th) fills much less OR much more
                           (a solid rectangle fills ~1.0, but at the WRONG
                           aspect — see below)
  largest_aspect_h_over_w  that component's own bounding-box height/width —
                           a notehead is close to 1 (CLAUDE.md Sec.10: "a
                           notehead is ~1.3 staff spaces wide", roughly as
                           tall), a whole/half rest is a WIDE, SHORT
                           rectangle (aspect << 1), and a quarter/8th/16th
                           rest is a TALL, thin stroke (aspect >> 1)

⚠️ THIS IS A MEASUREMENT SCRIPT, NOT A GATHER READER. `cv2.connectedComponents
WithStats` and `cv2.threshold(..., THRESH_OTSU)` need the RASTER, which
ADJUDICATE may never read (CLAUDE.md Sec.4a: it reads a frozen log). Whether
this feature can ship as an ADJUDICATE rule at all, or has to become a GATHER
quantity first, is the question Part B's own report answers — this script
only measures.

⚠️ THE POPULATION IS PRINT-CONFIRMED FOR EXACTLY ONE ROW. Everything else
below is UNCONFIRMED; the gap either separates a labelled point from an
unlabelled population (evidence about where the OTHER rows probably sit) or
it does not, and if it does not this MUST NOT ship (CLAUDE.md rule 5).
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

from tools.omr.staged.record_io import load_record          # noqa: E402

#: The two scan count pages, CLAUDE.md Sec.6a — paths as the acceptance
#: manifest (`benchmarks/acceptance/manifest.json`) names them, resolved
#: against the library root a worktree symlinks in.
DOCS: Dict[str, Dict[str, Any]] = {
    "litolff": {
        "record": "library/_shared-records/"
                  "beethoven5-litolff-mvt1-whole-20260923.record.json",
        "pdf": "library/editions/beethoven/symphony-5-op67/"
              "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870"
              "--imslp984073.pdf",
        "page": 3,
    },
    "breitkopf": {
        "record": "library/_shared-records/"
                  "brahms1-breitkopf-mvt1-whole-20260923.record.json",
        "pdf": "library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms"
              "--imslp317803.pdf",
        "page": 1,
    },
}

#: Sean's one confirmed case, 2026-09-27 (crop 5 of the cal-other-to-decided
#: batch): a `restWhole` box the detector drew that is really a quarter
#: notehead. Its subject and detector-reported step are on the record;
#: nothing else here has been shown to him.
SEAN_CONFIRMED_NOTEHEAD_SUBJECT = "glyph/3/1/4/8/8"


def _rest_boxes_on_page(rec: dict, page: int) -> List[Dict[str, Any]]:
    """Every `Q.REST` row on this page, with its own `Q.GLYPH_BOX` joined in.

    ⚠️ SAME-SUBJECT JOIN, NOT A FRAME/CLASS/POINT ONE: `Q.REST` is gathered on
    the glyph's own subject (`gather.py`'s rest reader), so a rest's box is
    the `Q.GLYPH_BOX` row filed on that SAME subject — the ordinary case,
    unlike the key-signature marker in Part A.
    """
    boxes: Dict[str, dict] = {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            boxes[o["subject"]] = o
    out: List[Dict[str, Any]] = []
    for o in rec["observations"]:
        if o["quantity"] != "rest":
            continue
        subject = o["subject"]
        bits = subject.split("/")
        if len(bits) < 2 or bits[0] != "glyph":
            continue
        try:
            subj_page = int(bits[1])
        except ValueError:
            continue
        if subj_page != page:
            continue
        box = boxes.get(subject)
        if box is None:
            out.append({"subject": subject, "class": str(o["value"]),
                       "page_box": None, "reason": "no_glyph_box"})
            continue
        page_box = (box.get("detail") or {}).get("bbox_page_px")
        out.append({"subject": subject, "class": str(o["value"]),
                   "page_box": page_box})
    return out


def _ink_features(arr, box) -> Optional[Dict[str, Any]]:
    """The two shape features (plus their inputs), measured on ONE crop.

    `arr` is a full-page GRAYSCALE array (uint8, 0 = black); `box` is
    `(x0, y0, x1, y1)` in that array's own pixel frame — the DETECTOR's own
    box, never padded, because the question is what the box's OWN ink looks
    like, not its neighbourhood.
    """
    import numpy as np
    import cv2

    x0, y0, x1, y1 = (int(round(v)) for v in box)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(arr.shape[1], x1), min(arr.shape[0], y1)
    if x1 <= x0 or y1 <= y0:
        return None
    crop = arr[y0:y1, x0:x1]
    if crop.dtype != np.uint8:
        crop = crop.astype(np.uint8)
    if crop.size == 0 or crop.max() == crop.min():
        # ⚠️ A UNIFORM CROP HAS NO OTSU SPLIT — declined, not defaulted to
        # all-ink or all-background.
        return None
    _, ink_img = cv2.threshold(crop, 0, 255,
                               cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = (ink_img > 0).astype(np.uint8)
    total = int(ink.sum())
    box_area = int(ink.size)
    fill_ratio = round(total / box_area, 4) if box_area else None
    if total == 0:
        return {"fill_ratio": fill_ratio, "n_components": 0,
                "largest_share": None, "largest_aspect_h_over_w": None,
                "largest_fill_ratio": None, "largest_w": None,
                "largest_h": None}
    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(ink, 8)
    comps = [(i, int(stats[i, cv2.CC_STAT_AREA])) for i in range(1, n)]
    if not comps:
        return {"fill_ratio": fill_ratio, "n_components": 0,
                "largest_share": None, "largest_aspect_h_over_w": None,
                "largest_fill_ratio": None, "largest_w": None,
                "largest_h": None}
    comps.sort(key=lambda t: -t[1])
    li, larea = comps[0]
    lw = int(stats[li, cv2.CC_STAT_WIDTH])
    lh = int(stats[li, cv2.CC_STAT_HEIGHT])
    return {
        "fill_ratio": fill_ratio,
        "n_components": len(comps),
        "largest_share": round(larea / total, 4) if total else None,
        "largest_aspect_h_over_w": round(lh / lw, 4) if lw else None,
        "largest_fill_ratio": round(larea / (lw * lh), 4) if lw and lh
                              else None,
        "largest_w": lw, "largest_h": lh,
    }


def _measure_document(name: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    import fitz
    from PIL import Image
    import numpy as np

    record_path = _REPO / spec["record"]
    pdf_path = _REPO / spec["pdf"]
    page = spec["page"]
    print(f"[{name}] loading {record_path.name} ...", flush=True)
    d = load_record(str(record_path))
    rec = d["record"]
    prov = d.get("provenance") or {}
    dpi = int(((prov.get("settings") or {}).get("args") or {}).get("dpi")
             or 600)
    print(f"[{name}] loaded; dpi={dpi}; extracting page {page} rest boxes",
          flush=True)
    rows = _rest_boxes_on_page(rec, page)
    del rec, d                                    # the record is huge; drop it
    print(f"[{name}] {len(rows)} rest rows on page {page} "
          f"({sum(1 for r in rows if r.get('page_box'))} with a page box)",
          flush=True)

    doc = fitz.open(str(pdf_path))
    pm = doc[page].get_pixmap(dpi=dpi)
    im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
          if pm.n >= 3 else
          Image.frombytes("L", (pm.width, pm.height), pm.samples)
          .convert("RGB"))
    arr = np.asarray(im.convert("L"), dtype=np.uint8)
    doc.close()

    measured: List[Dict[str, Any]] = []
    for r in rows:
        if not r.get("page_box"):
            measured.append({**r, "features": None})
            continue
        feats = _ink_features(arr, r["page_box"])
        measured.append({**r, "features": feats})
    return {"document": name, "dpi": dpi, "page": page,
           "n_rows": len(rows), "rows": measured}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--doc", choices=sorted(DOCS), default=None,
                    help="one document only (default: both)")
    a = ap.parse_args()

    docs = {a.doc: DOCS[a.doc]} if a.doc else DOCS
    out: Dict[str, Any] = {"documents": {}}
    for name, spec in docs.items():
        out["documents"][name] = _measure_document(name, spec)

    # ── the known case, named explicitly ────────────────────────────────────
    known = None
    for doc in out["documents"].values():
        for r in doc["rows"]:
            if r["subject"] == SEAN_CONFIRMED_NOTEHEAD_SUBJECT:
                known = r
    out["sean_confirmed_notehead"] = known

    Path(a.out).write_text(json.dumps(out, indent=1))
    total = sum(d["n_rows"] for d in out["documents"].values())
    measured = sum(1 for d in out["documents"].values() for r in d["rows"]
                  if r.get("features"))
    print(f"\n{total} rest rows across {len(docs)} document(s), "
          f"{measured} measured (had a page box and a non-uniform crop)")
    if known is not None:
        print("SEAN'S CONFIRMED NOTEHEAD:", json.dumps(known, indent=1))
    else:
        print("⚠️ SEAN'S CONFIRMED SUBJECT WAS NOT FOUND ON EITHER PAGE.")
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
