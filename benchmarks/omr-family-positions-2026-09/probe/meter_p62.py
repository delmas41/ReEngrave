#!/usr/bin/env python3
"""What `Q.METER_GLYPH_POSITION` SAYS about Litolff Beethoven 5 p.62.

    python3 benchmarks/omr-family-positions-2026-09/probe/meter_p62.py \
        library/editions/.../imslp984073.pdf --page 62 \
        --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt

⚠️⚠️ **THIS IS A DEMONSTRATION, NOT A VERDICT, AND THE DISTINCTION IS THE
WHOLE POINT.** The brief that commissioned this work called the p.62 case *"the
falsifier for the whole idea"* and said a position fact *"refuses it on
geometry alone"*. **Both are withdrawn.** Sean, 2026-09-17:

> *"I want to make sure that we keep clear that position is an option for
> helping us determine something but will rarely be a clear rule that
> determines by itself. 2 numbers not connected, one in the upper half and one
> in the lower half, could be a time signature. Due to ink bleed they may
> appear connected, or other things that we can't determine... Quick rules
> will give us quick results that could be poor."*

So this probe asks only: **does the position fact CONTRIBUTE anything here —
is there a measurable difference between what is printed and what is read?**
It does not ask whether the difference is big enough to decide on, it applies
no threshold, and **a result that does not separate the two is the expected
outcome and is not a negative result about the position facts.**

## WHAT THE PRINT HOLDS (`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` §6)

* The printed `3/4` is at **CELL 6**, on every one of the 17 staves, right
  after a double barline under *Tempo I.*
* The detector fires **NOTHING** at cell 6 on any staff.
* At **CELL 8** — an empty rest bar — it fires six `timeSig*` boxes on two
  staves, all at `x = 0.00`, the cell's LEFT EDGE, 0.35-0.40 staff spaces
  wide. Staff 11's `timeSig3` + `timeSig4` are **two vertically-adjacent
  fragments of ONE BARLINE**, and `_meter_from_digits` — which asks for two
  `timeSig*` glyphs at two different `y_center` values and nothing else —
  reads them as the meter.

⚠️ **SO THE BRIEF'S OWN COMPARISON CANNOT BE RUN.** It asked whether the
position fact distinguishes *"cell 6 (two marks, upper and lower halves, on 17
staves)"* from *"cell 8 (one stroke crossing the staff)"*. **There is no ink
at cell 6 to measure**: the comparison has one side. What CAN be shown is what
the fact says about the fragments that ARE read, which is what this prints.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from tools.omr.staged import gather as G                       # noqa: E402
from tools.omr.staged import pipeline as P                     # noqa: E402
from tools.omr.staged import positions as POS                  # noqa: E402
from tools.omr.staged.record import Observation, Q             # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=62)
    ap.add_argument("--weights", default=None)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    det = None
    if a.weights:
        from tools.omr.yolo_detector import YoloDetector
        det = YoloDetector(a.weights)

    os.environ[POS.POSITIONS_ENV] = "1"
    assert POS.positions_enabled()
    prepared = P.prepare_pages(a.pdf, [a.page], dpi=a.dpi)
    log = G.gather(prepared, detector=det, pdf_path=a.pdf,
                   surya_fallback=False, ocr_fallback=False)

    glyphs, posns = [], []
    for row in log.all_rows():
        if not isinstance(row, Observation):
            continue
        if row.quantity == Q.METER_GLYPH:
            glyphs.append(row)
        elif row.quantity == Q.METER_GLYPH_POSITION:
            posns.append(row)

    print(f"page {a.page}   Q.METER_GLYPH rows {len(glyphs)}   "
          f"Q.METER_GLYPH_POSITION rows {len(posns)}")
    print()

    # ── REACH FIRST: which cells carry any meter ink at all ─────────────────
    cells = sorted({int(r.detail.get("cell", -1)) for r in glyphs})
    print(f"cells with ANY timeSig detection: {cells}")
    print("  (the print puts the 3/4 at CELL 6 on all 17 staves; anything "
          "else here is ink the page does not print a meter at)")
    print()

    if not posns:
        print("⚠️⚠️ DEAD: no meter position rows on this page. Nothing was "
              "measured and nothing below would mean anything.")
        return 1

    rows = []
    print(f"{'staff':>5s} {'cell':>4s} {'class':14s} {'conf':>5s} "
          f"{'top':>6s} {'bot':>6s} {'height':>6s} {'half':>7s} "
          f"{'off-mid':>8s}")
    print("-" * 74)
    conf_of = {(r.subject.to_key(), int(r.detail.get("cell", -1)),
                float(r.detail.get("x", 0))): (r.value, r.score)
               for r in glyphs}
    for r in sorted(posns, key=lambda r: (int(r.detail.get("cell", -1)),
                                          r.subject.to_key())):
        cell = int(r.detail.get("cell", -1))
        key = (r.subject.to_key(), cell, float(r.detail.get("x", 0)))
        cls, conf = conf_of.get(key, (r.detail.get("detector_class"), None))
        staff = r.subject.to_key().rsplit("/", 1)[-1]
        rows.append({
            "staff": staff, "cell": cell, "class": cls, "conf": conf,
            "top": r.detail["top"], "bottom": r.detail["bottom"],
            "height_steps": r.detail["height_steps"],
            "half": r.detail["half"],
            "centre_steps_from_middle": r.detail["centre_steps_from_middle"],
            "staff_height_fraction": r.detail["staff_height_fraction"],
        })
        print(f"{staff:>5s} {cell:>4d} {str(cls):14s} "
              f"{(f'{conf:.2f}' if conf is not None else '  -  '):>5s} "
              f"{r.detail['top']:6.2f} {r.detail['bottom']:6.2f} "
              f"{r.detail['height_steps']:6.2f} {r.detail['half']:>7s} "
              f"{r.detail['centre_steps_from_middle']:+8.2f}")

    print()
    halves = {}
    for r in rows:
        halves.setdefault(r["half"], 0)
        halves[r["half"]] += 1
    print(f"`half` distribution over the meter ink actually read: {halves}")
    print()
    print("── WHAT THIS DOES AND DOES NOT SHOW ─────────────────────────────")
    print("  CONTRIBUTES: the fact is on the record, per glyph, staff-relative")
    print("    and scoreless, where before this page's meter ink carried a")
    print("    class, a confidence and an `x` and no vertical position at all.")
    print("    A later stage can now weigh WHERE the ink stood.")
    print("  DOES NOT SHOW: that geometry settles it. Ink bleed fuses two")
    print("    digits into one stroke, so a `spans` reading is compatible")
    print("    with a real meter; and two fragments in two halves are what a")
    print("    broken barline looks like too. Neither shape decides.")
    print("  CANNOT SHOW: a cell-6-vs-cell-8 comparison. The detector fires")
    print("    NOTHING at cell 6, where the meter is printed, so the")
    print("    comparison the brief asked for has only one side. That is a")
    print("    DETECTION gap and no position fact reaches it.")

    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(
            {"pdf": a.pdf, "page": a.page, "dpi": a.dpi,
             "cells_with_meter_ink": cells, "rows": rows,
             "half_distribution": halves}, indent=2, sort_keys=True))
        print(f"\n   wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
