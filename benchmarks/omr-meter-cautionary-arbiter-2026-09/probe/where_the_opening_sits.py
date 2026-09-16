#!/usr/bin/env python3
"""WHY A SAME-FRAME CONTEST CANNOT BE BUILT: an OPENING meter is not in the
first four staff spaces of its bar.

`score_frames.py` measured, on a real movement start that prints a `C` on every
staff (Brahms 1 / Breitkopf p.45, *Adagio*), that the 16-space HEADER window
reads it on **16 staves of 16** while the 4-space BAR-HEAD window of the same
cell reads it on **0 of 16** — and spells junk (`5/4`, `12/16`, `9/4`) when
forced below the floor.

That is not a threshold and not bias: it is where the ink is. A staff opens with
a CLEF and a KEY SIGNATURE, and only then the meter, so the first four spaces of
cell 0 hold a clef. This probe sweeps the window width on that one page and
reports the width at which the printed meter enters — turning the zero into a
DISTANCE.

⚠️ IT IS ABOUT THE OPENING ONLY. A mid-staff meter CHANGE is printed directly
after a barline with no clef in front of it, which is exactly why
`_bar_head_window` is four spaces wide and why this result does not argue
against the base branch's own mechanism. What it kills is the idea of asking
the same four-space question at CELL 0 so that the two sides of a cautionary
contest share a frame.

    python3 .../probe/where_the_opening_sits.py
    python3 .../probe/where_the_opening_sits.py --check   # non-zero if DEAD
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.time_signature_locator import (                 # noqa: E402
    DEFAULT_LOCATOR_CONFIG, locate_time_signature)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from score_frames import _page, _bar_head_window                # noqa: E402

from tools.omr.header_ink import staff_metrics                 # noqa: E402
from tools.omr.measure_extractor import (detect_barlines,      # noqa: E402
                                         extract_measures)
from tools.omr.staff_detector import detect_staves             # noqa: E402
from tools.omr.staff_header import header_cells_for_page       # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines    # noqa: E402

#: The movement START this probe is about. Its print was LOOKED AT: page number
#: 46, the word *Adagio*, full instrument names in the margin, and a common-time
#: `C` on every staff — so the right answer here is known without a truth file.
PAGE = "benchmarks/omr-veto-refusal-pricing-2026-09/out/brahms1/page045_full.png"
TRUTH_RAW = "C"

WIDTHS = [4.0, 6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 20.0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--out", default=str(
        pathlib.Path(__file__).resolve().parents[1]
        / "out" / "where-the-opening-sits.json"))
    args = ap.parse_args()

    path = ROOT / args.page
    pws = detect_barlines(detect_staves(_page(path)))
    cells = extract_measures(pws)
    remove_staff_lines(cells)
    headers = header_cells_for_page(pws)
    floor = DEFAULT_LOCATOR_CONFIG.min_score

    opening = {c.staff_index: c for c in cells if c.measure_index == 0}
    print(f"REACH  staves with a cell 0 = {len(opening)}  "
          f"headers = {len(headers)}  floor = {floor}  truth = {TRUTH_RAW}")
    if not opening:
        print("DEAD: no opening cell on this page")
        return 2

    table = {}
    for spaces in WIDTHS:
        right = 0
        answered = 0
        scores = []
        for staff_index, cell in sorted(opening.items()):
            window = _bar_head_window(cell, spaces)
            if window is None:
                continue
            trace = {}
            found = locate_time_signature(window, trace=trace)
            ranked = trace.get("scores") or []
            if ranked:
                scores.append(ranked[0]["score"])
            if found is not None:
                answered += 1
                if found.raw == TRUTH_RAW:
                    right += 1
        table[spaces] = {"answered": answered, "right": right,
                         "median_best": (round(statistics.median(scores), 4)
                                         if scores else None)}
        print(f"  bar head {spaces:>5.1f} spaces   answered {answered:>3}/"
              f"{len(opening)}   RIGHT ({TRUTH_RAW}) {right:>3}   "
              f"median best score {table[spaces]['median_best']}")

    # The shipped header window, for comparison — the reader as it runs today.
    hits = 0
    right = 0
    widths = []
    for staff_index, crop in sorted(headers.items()):
        metrics = staff_metrics(crop)
        if metrics and crop.image is not None:
            widths.append(crop.image.shape[1] / metrics[0])
        found = locate_time_signature(crop)
        if found is not None:
            hits += 1
            if found.raw == TRUTH_RAW:
                right += 1
    hdr_spaces = round(statistics.median(widths), 2) if widths else None
    print(f"  HEADER window {hdr_spaces} spaces   answered {hits}/"
          f"{len(headers)}   RIGHT ({TRUTH_RAW}) {right}")

    payload = {"page": args.page, "truth": TRUTH_RAW, "floor": floor,
               "n_opening_cells": len(opening), "bar_head": table,
               "header": {"spaces": hdr_spaces, "answered": hits,
                          "right": right, "n": len(headers)}}
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1))
    print(f"wrote {args.out}")

    if args.check:
        # ⚠️ The POSITIVE CONTROL is the header row: if the reader cannot read
        # this meter at ANY width, the probe is measuring a dead instrument and
        # its zeros mean nothing.
        if right == 0:
            print("DEAD: the reader never read the printed meter, at any width")
            return 2
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
