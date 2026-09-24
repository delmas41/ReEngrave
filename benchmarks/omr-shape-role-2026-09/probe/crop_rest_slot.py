#!/usr/bin/env python3
"""ROADMAP 2.12b — the crops Sean adjudicates before any of this is acted on.

    python3 benchmarks/omr-shape-role-2026-09/probe/crop_rest_slot.py --all
    python3 .../crop_rest_slot.py --record <r.json> --pdf <plate> \\
        --label litolff --neither 12 --other 6

`benchmarks/omr-shape-role-2026-09/FINDINGS.md` §5, 2.12b: *Sean adjudicates
ten crops of the `lands_on_neither` population before any of it is acted on.*
This cuts twelve of those and six of the population the geometry CONTRADICTS,
because the two are different claims and a human looking only at the weak one
cannot tell a bad rule from a bad plate.

**A print check is a crop with a RULER** (CLAUDE.md §6b), so every crop
carries:

  * GREEN horizontals — this staff's five `Q.STAFF_LINES`, so the crop says
    WHICH staff it is about;
  * a BLUE dashed line at the WHOLE-rest slot and an ORANGE dashed line at
    the HALF-rest slot, drawn from the same `WHOLE_REST_STEP` /
    `HALF_REST_STEP` the adjudicator reads — the ruler, in the picture;
  * a RED CORNER BRACKET on the exact rest, never a margin tick at its x;
  * the measured step, the class, and the rule's verdict in the caption and
    in the `.json` sidecar.

⚠️ `_frame_ok` AND `_index` ARE IMPORTED from
`omr-infer-duration-print-2026-09/probe/crop_inferred.py`, not copied: a crop
whose frame control is a second copy of somebody else's is a crop whose
control has not been run. The control CAN fail and a refused crop is listed
in the manifest with its contrast rather than dropped.

⚠️ THE RULE'S VERDICT IS RECOMPUTED FROM THE RECORD BY CALLING
`rhythm._rest_slot_verdict`, never re-derived here. A crop pass that spells
the predicate a second time is a crop pass that can disagree with the code it
is evidence about.

⚠️ THE DPI IS THE GATHER'S OWN, read off `provenance.settings.args.dpi`. A
crop cut at a different DPI from the one the boxes were measured at puts every
rectangle in the wrong place, and it looks exactly like a reading error.

⚠️ IT WRITES TO `out/print/`, NOT `out/crops/` — `.gitignore` excludes
`benchmarks/**/crops/` and these are the artefact.

⚠️ `VERDICT_none_yet` is `null` on every sidecar and on the manifest. NOTHING
IN 2.12b HAS BEEN PRINT-CONFIRMED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "benchmarks" / "omr-infer-duration-print-2026-09"
                      / "probe"))

from crop_inferred import _frame_ok                               # noqa: E402
from tools.omr.staged.record_io import load_record                # noqa: E402
from tools.omr.staged.adjudicators import rhythm as RH            # noqa: E402


def _staff_of(subject: str) -> str:
    bits = subject.split("/")
    return "staff/%s/%s/%s" % (bits[1], bits[2], bits[3])


def _spread(rows: List[dict], n: int) -> List[dict]:
    """`n` rows spread evenly over the population, deterministically.

    ⚠️ NOT THE FIRST `n`. The first rows of a record are page 1 system 0, and
    twelve crops off one system would say nothing about a document whose two
    plates bow differently at the top and the bottom. Sorted by subject and
    sampled at a constant stride, so the sample is reproducible and spread.
    """
    rows = sorted(rows, key=lambda r: r["subject"])
    if len(rows) <= n:
        return rows
    stride = len(rows) / float(n)
    return [rows[int(i * stride)] for i in range(n)]


def _classify(rec: dict) -> Dict[str, List[dict]]:
    """Every `restWhole` / `restHalf` row, with the rule's own verdict on it."""
    boxes, lines, spacing = {}, {}, {}
    for o in rec["observations"]:
        q = o["quantity"]
        if q == "glyph_box":
            boxes[o["subject"]] = o
        elif q == "staff_lines":
            lines[o["subject"]] = o["value"]
        elif q == "staff_spacing":
            spacing[o["subject"]] = o["value"]

    # ⚠️ THE RULE'S OWN WORDS, imported from the module under evidence, so a
    # crop's filename and the record's `slot_says` cannot drift apart.
    out: Dict[str, List[dict]] = {RH.SLOT_NEITHER: [], RH.SLOT_OTHER: [],
                                  RH.SLOT_NOT_CONTRADICTED: [],
                                  "unmeasurable": []}
    for o in rec["observations"]:
        if o["quantity"] != "rest":
            continue
        name = str(o["value"])
        if name not in ("restWhole", "restHalf"):
            continue
        subj = o["subject"]
        staff = _staff_of(subj)
        box = boxes.get(subj)
        page_box = ((box.get("detail") or {}).get("bbox_page_px")
                    if box else None)
        ls, sp = lines.get(staff), spacing.get(staff)
        if not page_box or not ls or not sp:
            out["unmeasurable"].append({"subject": subj, "class": name})
            continue
        step = RH._staff_step(page_box, ls, sp)
        verdict = RH._rest_slot_verdict(name, step)
        if verdict is None:
            out["unmeasurable"].append({"subject": subj, "class": name})
            continue
        out[verdict].append({"subject": subj, "class": name, "step": step,
                             "page_box": page_box, "staff": staff,
                             "lines": ls, "spacing": float(sp)})
    return out


def _cut(a, rec_path: str, pdf: str, label: str, out_dir: Path) -> dict:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw

    d = load_record(rec_path)
    rec = d["record"]
    prov = d.get("provenance") or {}
    dpi = int(((prov.get("settings") or {}).get("args") or {}).get("dpi") or 600)

    groups = _classify(rec)
    print("%s: neither %d, other %d, not-contradicted %d, unmeasurable %d "
          "(dpi %d)"
          % (label, len(groups[RH.SLOT_NEITHER]), len(groups[RH.SLOT_OTHER]),
             len(groups[RH.SLOT_NOT_CONTRADICTED]),
             len(groups["unmeasurable"]), dpi), flush=True)

    jobs = ([(RH.SLOT_NEITHER, r)
             for r in _spread(groups[RH.SLOT_NEITHER], a.neither)]
            + [(RH.SLOT_OTHER, r)
               for r in _spread(groups[RH.SLOT_OTHER], a.other)])

    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    pages: Dict[int, Any] = {}
    frames: Dict[int, Any] = {}
    manifest: List[dict] = []
    refused: List[dict] = []

    for bucket, r in jobs:
        _, p, sy, st, cell, gi = r["subject"].split("/")
        p, sy, st = int(p), int(sy), int(st)
        if p not in pages:
            pm = doc[p].get_pixmap(dpi=dpi)
            im = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
                  if pm.n >= 3 else
                  Image.frombytes("L", (pm.width, pm.height),
                                  pm.samples).convert("RGB"))
            pages[p] = im
            frames[p] = np.asarray(im.convert("L"), dtype=float)
        im, arr = pages[p], frames[p]

        ok, contrast = _frame_ok(arr, r["lines"], r["spacing"])
        if not ok:
            refused.append({"subject": r["subject"], "bucket": bucket,
                            "why": "FRAME CONTROL FAILED",
                            "contrast": round(contrast, 2)})
            continue

        bx0, by0, bx1, by1 = [float(v) for v in r["page_box"]]
        pad = a.pad_spaces * r["spacing"]
        x0 = max(0, bx0 - pad)
        x1 = min(im.width, bx1 + pad)
        y0 = max(0, min(min(r["lines"]), by0) - pad)
        y1 = min(im.height, max(max(r["lines"]), by1) + pad)

        crop = im.crop((int(x0), int(y0), int(x1), int(y1)))
        zoom = 4
        crop = crop.resize((crop.width * zoom, crop.height * zoom),
                           Image.LANCZOS)
        dr = ImageDraw.Draw(crop)

        def Y(y):
            return (y - y0) * zoom

        def X(x):
            return (x - x0) * zoom

        for y in r["lines"]:                              # GREEN: the staff
            dr.line([(0, Y(y)), (crop.width, Y(y))], fill=(0, 170, 0), width=2)

        # ── THE RULER: the two slots this rest is being measured against ────
        bottom = max(r["lines"])
        half_px = r["spacing"] / 2.0
        rulers = {}
        for name, step, colour in (("restWhole", RH.WHOLE_REST_STEP,
                                    (0, 90, 255)),
                                   ("restHalf", RH.HALF_REST_STEP,
                                    (255, 140, 0))):
            yy = bottom - step * half_px
            rulers[name] = yy
            for sx in range(0, crop.width, 24):           # dashed
                dr.line([(sx, Y(yy)), (sx + 12, Y(yy))], fill=colour, width=3)

        # ── THE SUBJECT: a corner bracket on the exact rest ─────────────────
        arm = max(10, int(0.9 * r["spacing"] * zoom))
        red = (230, 0, 0)
        for (cx, cy, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                 (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(X(cx), Y(cy)), (X(cx) + dx * arm, Y(cy))], fill=red,
                    width=5)
            dr.line([(X(cx), Y(cy)), (X(cx), Y(cy) + dy * arm)], fill=red,
                    width=5)

        name = "%s-p%d-s%d-st%d-c%s-g%s-%s.png" % (
            label, p, sy, st, cell, gi, bucket)
        crop.save(out_dir / name)
        side = {
            "png": name,
            "caption": (
                "%s page %d, system %d, staff %d, bar-cell %s — the detector "
                "called this rectangle `%s`. Measured against this staff's own "
                "lines its centre stands at step %.2f, where a whole rest "
                "hangs at %.1f (BLUE dashes) and a half rest sits at %.1f "
                "(ORANGE dashes). The rule says %s. GREEN = the five "
                "Q.STAFF_LINES; RED corner bracket = the rest itself. "
                "QUESTION FOR SEAN: against the print, is this a whole rest, "
                "a half rest, or not a rest at all?"
                % (label, p, sy, st, cell, r["class"], r["step"],
                   RH.WHOLE_REST_STEP, RH.HALF_REST_STEP, bucket)),
            "subject": r["subject"], "bucket": bucket, "page": p,
            "dpi": dpi, "zoom": zoom,
            "frame_control": {"passed": True, "contrast": round(contrast, 2)},
            "detector_class": r["class"],
            "measured_staff_step": round(r["step"], 3),
            "convention": {"restWhole": RH.WHOLE_REST_STEP,
                           "restHalf": RH.HALF_REST_STEP,
                           "slack_half_steps": RH.REST_SLOT_SLACK,
                           "frame": "bottom line 0, one step per half space, "
                                    "up positive"},
            "what_the_rule_does": (
                "ABSTAIN `rest_stands_where_no_rest_hangs` — the rest is held "
                "out of the file and counted"
                if bucket == RH.SLOT_NEITHER else
                "NARROW over both values, the measured one first — EXPORT "
                "refuses to argmax it, so the rest is held out and counted"),
            "rest_page_px": [bx0, by0, bx1, by1],
            "staff_lines_page_px": list(r["lines"]),
            "ruler_page_px": {k: round(v, 2) for k, v in rulers.items()},
            "crop_page_px": [x0, y0, x1, y1],
            "VERDICT_none_yet": None,
        }
        (out_dir / (name[:-4] + ".json")).write_text(json.dumps(side, indent=1))
        manifest.append(side)
        print("  %s  (%s, step %.2f)" % (name, r["class"], r["step"]),
              flush=True)

    man = {
        "label": label, "record": rec_path, "pdf": pdf, "dpi": dpi,
        "provenance": {"commit": prov.get("commit"),
                       "dirty": prov.get("dirty")},
        "population": {k: len(v) for k, v in groups.items()},
        "crops": manifest, "refused": refused,
        "VERDICT_none_yet": None,
        "_readme": (
            "ROADMAP 2.12b. Twelve rests whose ink stands where NEITHER "
            "convention puts a rest and six the geometry says are the OTHER "
            "kind. `VERDICT_none_yet` is null on every crop and on this "
            "manifest: nothing in 2.12b has been adjudicated against the "
            "print, which is why the rule NARROWS and ABSTAINS and flips no "
            "value. A sample is a stride over the subject-sorted population, "
            "not the first N."),
    }
    (out_dir / ("MANIFEST-%s.json" % label)).write_text(
        json.dumps(man, indent=1))
    if refused:
        print("  refused: %s" % refused, flush=True)
    return man


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record")
    ap.add_argument("--pdf")
    ap.add_argument("--label")
    ap.add_argument("--all", action="store_true",
                    help="both SCAN documents of the acceptance manifest")
    ap.add_argument("--neither", type=int, default=12)
    ap.add_argument("--other", type=int, default=6)
    #: ⚠️ WIDE ENOUGH TO SEE THE BAR. A crop tight on the rectangle shows a
    #: rectangle, and the question Sean is being asked -- *is this a whole
    #: rest, a half rest, or not a rest at all* -- is answered from what is
    #: around it: the bar's other events, its barlines, and the staff above.
    ap.add_argument("--pad-spaces", type=float, default=9.0)
    ap.add_argument("--out-dir",
                    default="benchmarks/omr-shape-role-2026-09/out/print")
    a = ap.parse_args()

    out_dir = _REPO / a.out_dir if not Path(a.out_dir).is_absolute() \
        else Path(a.out_dir)

    if a.all:
        from tools.library.score_library import library_root
        man = json.loads(
            (_REPO / "benchmarks/acceptance/manifest.json").read_text())
        n = 0
        for doc in man["documents"]:
            if doc["kind"] != "scan":
                # ⚠️ The engraved record is the control that returns ZERO on
                # this family (216 of 216 agree); there is nothing to crop and
                # saying so is the point.
                print("skipping %s: engraved, 0 rows in either bucket"
                      % doc["id"], flush=True)
                continue
            root = (Path(library_root()) if doc["record"]["root"] == "library"
                    else _REPO)
            rp = root / doc["record"]["path"]
            proot = (Path(library_root()) if doc["pdf"]["root"] == "library"
                     else _REPO)
            pp = proot / doc["pdf"]["path"]
            if not rp.exists() or not pp.exists():
                print("MISSING %s" % doc["id"], flush=True)
                continue
            _cut(a, str(rp), str(pp), doc["id"], out_dir)
            n += 1
        return 0 if n else 1

    if not (a.record and a.pdf and a.label):
        ap.error("--all, or --record + --pdf + --label")
    _cut(a, a.record, a.pdf, a.label, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
