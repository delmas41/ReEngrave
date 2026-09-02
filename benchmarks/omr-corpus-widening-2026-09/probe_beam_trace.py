"""Trace `resolve_rhythms_for_cell`'s beam count, notehead by notehead.

Rebuilds one cell from the PDF (phase 1 + CV lines) and its YOLO detections
from the shipped `.omr.json`, then replays the exact counting path — stem
lookup, the top/bottom end partition, the cluster count — printing every beam
that reached each decision and why it was kept.

    python3 benchmarks/omr-corpus-widening-2026-09/probe_beam_trace.py \
        --work mozart-sym41-mvt1 --staff 1 --measure 0

Host Python.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_lines  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.rhythm import (  # noqa: E402
    BEAM_Y_CLUSTER_FACTOR, _deduplicate_beams, _overlaps_any_in_x,
    _spans_the_whole_cell, _staff_line_spacing, _stem_for_notehead,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@dataclass
class Det:
    smufl_name: str
    category: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 1.0
    pitch: str | None = None


def dets_from_json(doc, staff_index, measure_index):
    for p in doc["pages"]:
        for sy in p["systems"]:
            for st in sy["staves"]:
                if st["staff_index"] != staff_index:
                    continue
                for m in st["measures"]:
                    if m["measure_index"] != measure_index:
                        continue
                    out = []
                    for d in m["detections"]:
                        x, y, w, h = d["bbox"]
                        out.append(Det(d["class"], d.get("category", ""),
                                       int(x), int(y), int(w), int(h),
                                       d.get("confidence", 1.0), d.get("pitch")))
                    return out, m
    return [], None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--staff", type=int, required=True)
    ap.add_argument("--measure", type=int, required=True)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    doc = json.load(open(args.fixtures / f"{args.work}.omr.json"))
    dets, mjson = dets_from_json(doc, args.staff, args.measure)

    pg = render_page(args.fixtures / f"{args.work}.pdf", 0, dpi=args.dpi)
    from tools.omr.staff_detector import detect_staves as ds
    from tools.omr.staff_line_removal import remove_staff_lines
    pws = ds(pg)
    detect_barlines(pws)
    all_cells = extract_measures(pws)
    remove_staff_lines(all_cells)   # transcribe.py:3669 — must match the real run
    cell = None
    for c in all_cells:
        if (getattr(c, "staff_index", None) == args.staff
                and getattr(c, "measure_index", None) == args.measure):
            cell = c
            break
    if cell is None:
        print("cell not found")
        return 1

    sp = _staff_line_spacing(cell)
    tol = sp * BEAM_Y_CLUSTER_FACTOR
    extra = detect_lines(cell)
    cv_stems, cv_beams = extra["stems"], extra["beams"]

    yolo_beams = [d for d in dets
                  if d.category == "structural" and "beam" in d.smufl_name.lower()
                  and not _spans_the_whole_cell(d, cell)]
    beams = list(cv_beams) + [y for y in yolo_beams
                              if not _overlaps_any_in_x(y, cv_beams)]
    beams = _deduplicate_beams(beams, sp)

    print(f"cell w={cell.width} h={cell.height} spacing={sp:.1f} tol={tol:.1f} "
          f"end_window={tol * 4:.1f}")
    print(f"staff lines canonical: {getattr(cell, 'staff_line_ys_canonical', None)}")
    print(f"image_no_staff present: "
          f"{getattr(cell, 'image_no_staff', None) is not None}")
    print(f"\nBEAM LIST used by the counter ({len(beams)}: "
          f"{len(cv_beams)} cv + {len(beams) - len(cv_beams)} yolo):")
    for b in sorted(beams, key=lambda b: b.y_canonical):
        yc = b.y_canonical + b.height_canonical // 2
        full = b.width_canonical / cell.width
        print(f"  x={b.x_canonical:5d}..{b.x_canonical + b.width_canonical:5d} "
              f"yc={yc:5d} h={b.height_canonical:4d} conf={b.confidence:.2f} "
              f"width={full * 100:5.1f}% of cell"
              f"{'   <-- SPANS CELL' if full > 0.6 else ''}")

    print(f"\nSTEMS ({len(cv_stems)}):")
    for s in sorted(cv_stems, key=lambda s: s.x_canonical):
        print(f"  x={s.x_canonical:5d} y={s.y_canonical:5d}.."
              f"{s.y_canonical + s.height_canonical:5d} h={s.height_canonical:4d}")

    nhs = sorted([d for d in dets if d.category == "notehead"],
                 key=lambda d: d.x_canonical)
    print(f"\nPER-NOTEHEAD TRACE ({len(nhs)}):")
    for nh in nhs:
        nh_yc = nh.y_canonical + nh.height_canonical // 2
        stem = _stem_for_notehead(
            nh, cv_stems,
            max_x_distance=max(nh.width_canonical * 0.6, sp * 0.4))
        print(f"\n  NH x={nh.x_canonical} yc={nh_yc} {nh.smufl_name} "
              f"pitch={nh.pitch}")
        if stem is None:
            print("    no stem -> notehead fallback path")
            continue
        s_x_l, s_x_r = stem.x_canonical, stem.x_canonical + stem.width_canonical
        s_y_top = stem.y_canonical
        s_y_bot = stem.y_canonical + stem.height_canonical
        ew = tol * 4.0
        print(f"    stem x={s_x_l}..{s_x_r} y={s_y_top}..{s_y_bot}")
        top_ys, bot_ys = [], []
        for b in beams:
            b_x_l, b_x_r = b.x_canonical, b.x_canonical + b.width_canonical
            if b_x_r < s_x_l - 5 or b_x_l > s_x_r + 5:
                continue
            b_y_c = b.y_canonical + b.height_canonical // 2
            d_top, d_bot = abs(b_y_c - s_y_top), abs(b_y_c - s_y_bot)
            where = None
            if d_top <= ew and d_top <= d_bot:
                top_ys.append(b_y_c)
                where = "TOP"
            elif d_bot <= ew:
                bot_ys.append(b_y_c)
                where = "BOT"
            wide = (b.width_canonical / cell.width) > 0.6
            print(f"      beam yc={b_y_c:5d} d_top={d_top:5.0f} d_bot={d_bot:5.0f}"
                  f" -> {where or 'dropped'}"
                  f"{'  [spans cell]' if wide else ''}")

        def count(ys):
            if not ys:
                return 0
            ys = sorted(ys)
            n = 1
            for i in range(1, len(ys)):
                if ys[i] - ys[i - 1] > tol:
                    n += 1
            return n
        print(f"    top_ys={sorted(top_ys)} -> {count(top_ys)} levels")
        print(f"    bot_ys={sorted(bot_ys)} -> {count(bot_ys)} levels")
        print(f"    RESULT n_beam_levels = {max(count(top_ys), count(bot_ys))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
