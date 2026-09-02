"""Which STEMS change their beam-level count, and whether the change extends a stack.

`probe_sloped_beam_reach.py` counts (stem end, beam band) PAIRS. A pair is not
the unit that matters — a duration is set by the LEVEL COUNT, so a pair that
flips inside a cluster the stem already had changes nothing.

This one replays `_beams_attached_to_stem` under both rules and reports, per
STEM, the count before and after, split by the question that decides whether
the widening is recovering music or inventing it:

  * **extends a stack** — the stem already had >= 1 level and gains one. That is
    the second stroke of a sixteenth group reaching its outermost note, which
    is the fault under investigation.
  * **invents a first beam** — the stem had 0 levels and gains one. A quarter
    note becoming an eighth. This is the way the change could do harm, and it
    should be rare or absent.

    python3 benchmarks/omr-corpus-widening-2026-09/probe_beam_level_delta.py \
        --works ... --fixtures <dir>

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


@dataclass
class Det:
    """Minimal stand-in for a YOLO SymbolDetection, rebuilt from the .omr.json."""
    smufl_name: str
    category: str
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 1.0
    pitch: str | None = None


def yolo_beams_by_cell(doc):
    """(staff_index, measure_index) -> the cell's YOLO beam detections.

    ⚠️ The counter does NOT see the CV beams alone. `resolve_rhythms_for_cell`
    merges: CV beams win the columns they speak for, and a YOLO beam is kept
    wherever no CV beam overlaps its x-range. A probe that skips this
    UNDERSTATES the change — measured on `brahms-sym4-mvt1`, which shows no
    stem change on CV beams alone and does move by 2 edits end to end.
    """
    out: dict[tuple[int, int], list] = {}
    for p in doc["pages"]:
        for sy in p["systems"]:
            for st in sy["staves"]:
                for m in st["measures"]:
                    beams = []
                    for d in m["detections"]:
                        if d.get("category") != "structural":
                            continue
                        if "beam" not in d.get("class", "").lower():
                            continue
                        x, y, w, h = d["bbox"]
                        beams.append(Det(d["class"], "structural", int(x), int(y),
                                         int(w), int(h), d.get("confidence", 1.0)))
                    out[(st["staff_index"], m["measure_index"])] = beams
    return out


def count_levels(stem, beams, tol, *, to_band: bool):
    """`_beams_attached_to_stem`, with the distance rule switchable."""
    s_x_l = stem.x_canonical
    s_x_r = stem.x_canonical + stem.width_canonical
    s_y_top = float(stem.y_canonical)
    s_y_bot = s_y_top + stem.height_canonical
    ew = tol * 4.0
    top_ys, bot_ys = [], []
    for b in beams:
        if (b.x_canonical + b.width_canonical) < s_x_l - 5 or b.x_canonical > s_x_r + 5:
            continue
        b_yc = b.y_canonical + b.height_canonical // 2
        b_top = float(b.y_canonical)
        b_bot = b_top + b.height_canonical

        def d(y):
            if not to_band:
                return abs(b_yc - y)
            return 0.0 if b_top <= y <= b_bot else min(abs(b_top - y), abs(b_bot - y))

        d_top, d_bot = d(s_y_top), d(s_y_bot)
        if d_top <= ew and d_top <= d_bot:
            top_ys.append(b_yc)
        elif d_bot <= ew:
            bot_ys.append(b_yc)

    def c(ys):
        if not ys:
            return 0
        ys = sorted(ys)
        n = 1
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] > tol:
                n += 1
        return n
    return max(c(top_ys), c(bot_ys))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", nargs="+", required=True)
    ap.add_argument("--fixtures", type=Path, default=FIXTURES)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    transitions: Counter = Counter()
    per_work: dict[str, Counter] = {}
    examples: list[str] = []
    n_stems = 0
    for work in args.works:
        pdf = args.fixtures / f"{work}.pdf"
        if not pdf.exists():
            continue
        doc = json.load(open(args.fixtures / f"{work}.omr.json"))
        yolo = yolo_beams_by_cell(doc)
        pg = render_page(pdf, 0, dpi=args.dpi)
        pws = detect_staves(pg)
        detect_barlines(pws)
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        wc: Counter = Counter()
        for cell in cells:
            sp = _staff_line_spacing(cell)
            if sp <= 1.0:
                continue
            tol = sp * BEAM_Y_CLUSTER_FACTOR
            extra = detect_lines(cell)
            stems, cv_beams = extra["stems"], extra["beams"]
            # Reproduce resolve_rhythms_for_cell's merge exactly.
            yb = [b for b in yolo.get((getattr(cell, "staff_index", -1),
                                       getattr(cell, "measure_index", -1)), [])
                  if not _spans_the_whole_cell(b, cell)]
            beams = list(cv_beams) + [b for b in yb
                                      if not _overlaps_any_in_x(b, cv_beams)]
            beams = _deduplicate_beams(beams, sp)
            if not beams:
                continue
            for s in stems:
                n_stems += 1
                before = count_levels(s, beams, tol, to_band=False)
                after = count_levels(s, beams, tol, to_band=True)
                if before != after:
                    transitions[(before, after)] += 1
                    wc[(before, after)] += 1
                    if before == 0 or len(examples) < 14:
                        examples.append(
                            f"{'INVENTS ' if before == 0 else '        '}"
                            f"{work} staff {getattr(cell, 'staff_index', '?')} "
                            f"m{getattr(cell, 'measure_index', '?')} "
                            f"stem x={s.x_canonical} y={s.y_canonical} "
                            f"h={s.height_canonical} sp={sp:.0f} "
                            f"{before} -> {after}")
        per_work[work] = wc
        print(f"  {work}: {sum(wc.values())} stems change")

    print(f"\n{n_stems} stems examined, {sum(transitions.values())} change level")
    print("\ntransition  count   kind")
    extends = invents = 0
    for (b, a), n in sorted(transitions.items()):
        kind = ("EXTENDS a stack" if b >= 1 else "INVENTS a first beam")
        if b >= 1:
            extends += n
        else:
            invents += n
        print(f"   {b} -> {a}   {n:5d}   {kind}")
    print(f"\n  extends an existing stack : {extends}")
    print(f"  invents a first beam      : {invents}")
    print("\nexamples:")
    for e in examples:
        print("   ", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
