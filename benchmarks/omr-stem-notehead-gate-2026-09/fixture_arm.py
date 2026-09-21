"""THE GATE, RE-SCORED ON THE FIXTURES THAT JUSTIFIED THE RULE IT NARROWS.

`_drop_paired_strokes`' own docstring cites TWO measurements, and both are
still in the tree:

  1. the LilyPond REFERENCE SHEET (`benchmarks/omr-phase4-lines`), engraved at
     four staff-line thicknesses, truth 48 stems known BY CONSTRUCTION --
     *"from +7/+8/+5/+2 to -1/0/+1/0"*;
  2. FOURTEEN HAND-COUNTED CELLS across four scores
     (`hand-labeled-stems.json`) -- *"summed |error| from 60 to 24"*.

⚠️⚠️ A CHANGE TO `Q.STEM` MUST NOT SHIP WITHOUT RE-RUNNING THESE. That is the
whole point of this arm: the gate is a narrowing of a rule whose justification
is those two numbers, and `benchmarks/omr-stem-pair-rule-2026-09` scored the
gate on ONE of them (the cells) and never on the reference sheet.

⚠️ AND IT RUNS THE SHIPPED CODE, not a restatement. The sibling probe
implemented the gate inside itself because nothing in `tools/` had it; this
arm calls `detect_stems(..., noteheads=..., enable_notehead_gate=True)`, so a
divergence between what was measured and what ships is impossible rather than
merely unlikely.

⚠️ THE TWO TRUTHS ARE IN DIFFERENT CURRENCIES AND ARE NEVER SUMMED. The
reference sheet is signed per THICKNESS (it is a whole-page total against a
known 48); the hand cells are summed |error| over cells. `FINDINGS.md` of the
sibling lane states the deeper reason: the labeler counts *one stem per note
OR CHORD*, so a stroke costs 1 there and N heads in the staged record.

CONTROLS
  * REACH is printed first and the arm exits 2 declaring itself DEAD at zero.
  * POSITIVE: the three arms must not agree everywhere, or the gate is inert
    and every number is a clean believable zero.
  * The reference sheet needs `lilypond` on PATH and the cells need the score
    root; each half reports its own reach and the arm runs whichever it can.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_stems                     # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page                       # noqa: E402
from tools.omr.staff_detector import detect_staves                    # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines           # noqa: E402
from tools.omr.training.line_detection_eval import (                  # noqa: E402
    GROUND_TRUTH_PATH, HAND_STEMS_PATH, SCORE_ROOT, THICKNESSES,
    engrave, _resolve_cells)

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def heads_of(det, c):
    return [(float(d.x_canonical), float(d.y_canonical),
             float(d.width_canonical), float(d.height_canonical))
            for d in (det.detect(c) or [])
            if "notehead" in str(getattr(d, "smufl_name", "")).lower()]


def three_arms(cells, det):
    """(ON, OFF, GATED, noteheads) stem counts over `cells`.

    ON is the shipped call with no notehead argument at all -- which is what
    production does today, and is NOT the same statement as "the gate flag is
    off": it proves the default path is untouched by the new parameter.
    """
    on = off = gated = nh = 0
    for c in cells:
        heads = heads_of(det, c)
        nh += len(heads)
        on += len(detect_stems(c))
        off += len(detect_stems(c, drop_accidental_pairs=False))
        gated += len(detect_stems(c, noteheads=heads,
                                  enable_notehead_gate=True))
    return on, off, gated, nh


def reference_sheet(det, workdir: Path) -> dict | None:
    """The LilyPond sheet at four line thicknesses, truth 48 by construction."""
    if not shutil.which("lilypond"):
        print("== REFERENCE SHEET: DEAD -- lilypond not on PATH")
        return None
    gt = json.loads(GROUND_TRUTH_PATH.read_text())
    truth = sum(v["stems"] for v in gt["per_staff_totals"].values())
    rows = []
    print(f"== REFERENCE SHEET  (truth {truth} stems, known by construction)")
    print(f"{'thick':>6} {'ON':>5} {'OFF':>5} {'GATED':>6} "
          f"{'dON':>5} {'dOFF':>5} {'dGATED':>7} {'heads':>6}")
    for t in THICKNESSES:
        pdf = engrave(t, workdir)
        pws = detect_barlines(detect_staves(render_page(pdf, 0, dpi=600)))
        cells = extract_measures(pws)
        remove_staff_lines(cells)
        on, off, gated, nh = three_arms(cells, det)
        rows.append({"thickness": t, "truth": truth, "on": on, "off": off,
                     "gated": gated, "noteheads": nh})
        print(f"{t:>6} {on:>5} {off:>5} {gated:>6} "
              f"{on - truth:>+5} {off - truth:>+5} {gated - truth:>+7} "
              f"{nh:>6}")
    print(f"   summed |error|  ON {sum(abs(r['on'] - truth) for r in rows):3d}"
          f"   OFF {sum(abs(r['off'] - truth) for r in rows):3d}"
          f"   GATED {sum(abs(r['gated'] - truth) for r in rows):3d}")
    return {"truth": truth, "rows": rows}


def hand_cells(det) -> dict | None:
    """The 14 hand-counted cells across four scores."""
    if not HAND_STEMS_PATH.exists():
        print("== HAND CELLS: DEAD -- no hand-labeled-stems.json")
        return None
    data = json.loads(HAND_STEMS_PATH.read_text())
    pages, rows = {}, []
    err = {"on": 0, "off": 0, "gated": 0}
    print(f"\n== HAND-COUNTED CELLS")
    print(f"{'cell':>4} {'score':>14} {'truth':>6} {'ON':>5} {'OFF':>5} "
          f"{'GATED':>6} {'heads':>6}")
    for entry in data["cells"]:
        if entry["stems"] is None:
            continue
        spec = data["scores"][entry["score"]]
        pdf = SCORE_ROOT / spec.split(",")[0]
        if not pdf.exists():
            print(f"{entry['n']:>4} {entry['score']:>14}  pdf missing "
                  f"-- excluded")
            continue
        key = (entry["score"], entry["dpi"])
        if key not in pages:
            page_index = int(spec.rsplit(" ", 1)[-1])
            pws = detect_barlines(detect_staves(
                render_page(pdf, page_index, dpi=entry["dpi"])))
            cells = extract_measures(pws)
            remove_staff_lines(cells)
            pages[key] = cells
        group = _resolve_cells(pages[key], entry)
        if not group:
            # ⚠️ NOT A FAILURE OF THE GATE. `_resolve_cells`' own docstring
            # records that any phase-1 change re-segments the page; the
            # sibling lane measured 4 of 14 La Mer cells unresolvable on
            # today's tree. Excluded and COUNTED, never silently dropped.
            print(f"{entry['n']:>4} {entry['score']:>14}  region not "
                  f"resolvable -- excluded")
            continue
        on, off, gated, nh = three_arms(group, det)
        t = entry["stems"]
        for k, v in (("on", on), ("off", off), ("gated", gated)):
            err[k] += abs(v - t)
        rows.append({"n": entry["n"], "score": entry["score"], "truth": t,
                     "on": on, "off": off, "gated": gated, "noteheads": nh})
        print(f"{entry['n']:>4} {entry['score']:>14} {t:>6} {on:>5} {off:>5} "
              f"{gated:>6} {nh:>6}")
    if not rows:
        return None
    print(f"   REACH {len(rows)} of "
          f"{sum(1 for e in data['cells'] if e['stems'] is not None)} "
          f"scoreable cells")
    print(f"   summed |error|  ON {err['on']:3d}   OFF {err['off']:3d}   "
          f"GATED {err['gated']:3d}")
    for k in ("off", "gated"):
        w = sum(1 for r in rows
                if abs(r[k] - r["truth"]) > abs(r["on"] - r["truth"]))
        b = sum(1 for r in rows
                if abs(r[k] - r["truth"]) < abs(r["on"] - r["truth"]))
        print(f"   {k.upper():>5} vs ON: worse on {w}, better on {b}, "
              f"equal on {len(rows) - w - b}")
    return {"summed_abs_error": err, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--json", default=str(HERE / "out" / "fixtures.json"))
    ap.add_argument("--skip-reference", action="store_true")
    a = ap.parse_args()
    if not Path(a.weights).exists():
        print(f"DEAD: no weights at {a.weights} -- the gate needs the "
              f"detector and cannot be exercised without it.")
        return 2
    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)

    ref = None
    if not a.skip_reference:
        with tempfile.TemporaryDirectory() as td:
            ref = reference_sheet(det, Path(td))
    cells = hand_cells(det)

    if ref is None and cells is None:
        print("\nDEAD: neither fixture could be scored.")
        return 2

    # POSITIVE CONTROL -- the three arms must not agree everywhere.
    allrows = (ref["rows"] if ref else []) + (cells["rows"] if cells else [])
    if all(r["on"] == r["off"] == r["gated"] for r in allrows):
        print("\nDEAD: POSITIVE CONTROL FAILED -- all three arms agree on "
              "every row. The gate is inert here and no number below means "
              "anything.")
        return 2
    n_h = sum(r["noteheads"] for r in allrows)
    if n_h == 0:
        print("\nDEAD: the detector found NO noteheads anywhere -- GATED is "
              "just OFF.")
        return 2
    print(f"\n== POSITIVE CONTROL: the arms differ; {n_h} noteheads detected "
          f"over {len(allrows)} rows.")

    out = {"weights": a.weights, "reference_sheet": ref, "hand_cells": cells}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
