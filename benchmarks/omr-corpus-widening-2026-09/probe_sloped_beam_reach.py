"""How far a stem end sits from its beam — measured to the box CENTRE and to the BOX.

`rhythm._beams_attached_to_stem` decides which beams belong to a stem by the
distance from the stem's end to each beam's box CENTRE, against a fixed
`end_window` of 4 x the clustering tolerance.

A beam box does not sit at its stroke, though. A SLOPED beam's box spans the
whole vertical excursion of the stroke, so the stroke is at the box's TOP at
one end of the group and at its BOTTOM at the other, while the centre is a y
the stroke only occupies in the middle. The outermost stem of a rising group
is therefore measured against a y that is half a box-height wrong, in the
direction that pushes it out of the window.

`line_detection._attached_stem_count` already makes the opposite choice for the
same reason, and says so in its docstring.

This probe measures the size of that bias over every beam a corpus contains:

  * `d_centre`  — the distance the code uses today
  * `d_box`     — the distance to the box as an INTERVAL (0 when the stem end
                  is inside the box's y-range), which is what the stroke's
                  true position can never be further than
  * `d_centre - d_box`, which is bounded by half the box height by construction
  * whether the pair FLIPS: rejected on the centre, admitted on the box

    python3 benchmarks/omr-corpus-widening-2026-09/probe_sloped_beam_reach.py \
        --works mozart-sym41-mvt1 ... --fixtures <dir> --csv out.csv

Host Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_lines  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.rhythm import (  # noqa: E402
    BEAM_Y_CLUSTER_FACTOR, _deduplicate_beams, _overlaps_any_in_x,
    _spans_the_whole_cell, _staff_line_spacing,
)
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_beam_level_delta import yolo_beams_by_cell  # noqa: E402


def interval_distance(p: float, lo: float, hi: float) -> float:
    """Distance from point `p` to the closed interval [lo, hi]; 0 when inside."""
    if p < lo:
        return lo - p
    if p > hi:
        return p - hi
    return 0.0


def pairs_for_cell(cell, yolo_beams=()):
    """Every (stem end, beam band) pair the x-overlap filter admits.

    ⚠️ Takes the cell's YOLO beams too, because the counter does NOT see the CV
    list alone — `resolve_rhythms_for_cell` keeps a YOLO beam wherever no CV
    beam overlaps its x-range. A CV-only version of this probe reported zero
    changed stems on `brahms-sym4-mvt1`, which moves by 2 edits end to end.
    """
    sp = _staff_line_spacing(cell)
    if sp <= 1.0:
        return []
    tol = sp * BEAM_Y_CLUSTER_FACTOR
    end_window = tol * 4.0
    extra = detect_lines(cell)
    stems, cv_beams = extra["stems"], extra["beams"]
    yb = [b for b in yolo_beams if not _spans_the_whole_cell(b, cell)]
    beams = list(cv_beams) + [b for b in yb if not _overlaps_any_in_x(b, cv_beams)]
    beams = _deduplicate_beams(beams, sp)
    rows = []
    for s in stems:
        s_x_l = s.x_canonical
        s_x_r = s.x_canonical + s.width_canonical
        s_y_top = float(s.y_canonical)
        s_y_bot = s_y_top + s.height_canonical
        for b in beams:
            b_x_l = b.x_canonical
            b_x_r = b.x_canonical + b.width_canonical
            if b_x_r < s_x_l - 5 or b_x_l > s_x_r + 5:
                continue
            b_top = float(b.y_canonical)
            b_bot = b_top + b.height_canonical
            b_yc = b.y_canonical + b.height_canonical // 2
            for end_name, s_y in (("top", s_y_top), ("bot", s_y_bot)):
                d_centre = abs(b_yc - s_y)
                d_box = interval_distance(s_y, b_top, b_bot)
                rows.append(dict(
                    spacing=sp, end_window=end_window, end=end_name,
                    d_centre=d_centre, d_box=d_box,
                    bias=d_centre - d_box,
                    band_h=float(b.height_canonical),
                    band_h_sp=b.height_canonical / sp,
                    beam_w_sp=b.width_canonical / sp,
                    in_centre=d_centre <= end_window,
                    in_box=d_box <= end_window,
                ))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", nargs="+", required=True)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--csv", type=Path)
    args = ap.parse_args()

    allrows = []
    for work in args.works:
        pdf = args.fixtures / f"{work}.pdf"
        if not pdf.exists():
            print(f"  (skip {work}: no pdf)")
            continue
        pg = render_page(pdf, 0, dpi=args.dpi)
        pws = detect_staves(pg)
        detect_barlines(pws)
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        yolo = yolo_beams_by_cell(json.load(open(args.fixtures / f"{work}.omr.json")))
        n = 0
        for cell in cells:
            yb = yolo.get((getattr(cell, "staff_index", -1),
                           getattr(cell, "measure_index", -1)), [])
            for r in pairs_for_cell(cell, yb):
                r.update(work=work,
                         staff=getattr(cell, "staff_index", None),
                         measure=getattr(cell, "measure_index", None))
                allrows.append(r)
                n += 1
        print(f"  {work}: {len(cells)} cells, {n} (stem end, beam band) pairs")

    print(f"\n{len(allrows)} pairs over {len(args.works)} works")

    # The bias is half the band height by construction when the stem end is
    # outside the band; show the band-height distribution it is driven by.
    print("\nBAND HEIGHT (staff spaces) — what the bias is half of:")
    hb = Counter()
    for r in allrows:
        hb[round(r["band_h_sp"] * 4) / 4] += 1
    for k in sorted(hb):
        print(f"   {k:5.2f} sp  {hb[k]:6d}  {'#' * min(60, hb[k] // 20)}")

    flips = [r for r in allrows if r["in_box"] and not r["in_centre"]]
    both = [r for r in allrows if r["in_box"] and r["in_centre"]]
    neither = [r for r in allrows if not r["in_box"] and not r["in_centre"]]
    print(f"\nadmitted by BOTH rules      {len(both):6d}")
    print(f"FLIPS (box admits, centre rejects) {len(flips):6d}")
    print(f"admitted by NEITHER         {len(neither):6d}")
    assert not [r for r in allrows if r["in_centre"] and not r["in_box"]], \
        "the box rule is a strict widening; nothing may be lost"

    def summ(name, rows, key):
        if not rows:
            print(f"  {name}: none")
            return
        vs = sorted(r[key] for r in rows)
        q = lambda f: vs[min(len(vs) - 1, int(f * len(vs)))]  # noqa: E731
        print(f"  {name:28s} n={len(vs):6d}  min={vs[0]:6.1f} p25={q(.25):6.1f} "
              f"med={q(.5):6.1f} p75={q(.75):6.1f} max={vs[-1]:6.1f}")

    print("\nd_box (distance to the band as an interval), in px:")
    summ("admitted by both", both, "d_box")
    summ("FLIPPED", flips, "d_box")
    print("\nband height (staff spaces):")
    summ("admitted by both", both, "band_h_sp")
    summ("FLIPPED", flips, "band_h_sp")
    print("\nbias = d_centre - d_box, in px:")
    summ("admitted by both", both, "bias")
    summ("FLIPPED", flips, "bias")

    print("\nFLIPS per work:")
    for w, n in Counter(r["work"] for r in flips).most_common():
        tot = sum(1 for r in allrows if r["work"] == w)
        print(f"   {w:28s} {n:5d} of {tot:6d} pairs")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as fh:
            wtr = csv.DictWriter(fh, fieldnames=list(allrows[0].keys()))
            wtr.writeheader()
            wtr.writerows(allrows)
        print(f"\nwrote {args.csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
