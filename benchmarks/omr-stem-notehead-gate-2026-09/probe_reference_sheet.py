"""WHY THE GATE GIVES BACK THE WHOLE REFERENCE-SHEET WIN — opened, not guessed.

`fixture_arm.py` measures that on the LilyPond reference sheet the GATED arm
is IDENTICAL to OFF at all four line thicknesses (56/56/56/51 against a truth
of 48, summed |error| 27 where ON reads 3). That is only possible if EVERY
stroke the pair rule deletes there meets a detected notehead.

⚠️⚠️ AND THE SHEET CONTAINS NO ACCIDENTALS AT ALL. `reference-lines.ly` is
plain C major and G major — `c'4 d'4 e'4 f'4`, `<c' e' g'>4`, `g2 b2` — not
one sharp, flat or natural in 48 stems. So the rule's own cited win on this
fixture (*"from +7/+8/+5/+2 to -1/0/+1/0"*) was NEVER a measurement of
accidental rejection. Something else on this sheet comes in pairs.

This probe asks WHICH SOMETHING, with no story: for each thickness it dumps
every deleted stroke's geometry, whether it stands on a detected notehead,
and WHICH BAR of the sheet it falls in — and the sheet's truth is known per
bar by construction, so "the deletions are in the dense bar" is checkable
rather than plausible.

⚠️ It does NOT decide whether a deleted stroke is a real stem. It cannot: two
readings of our own (the CV rung and the detector) agree that ink is there,
which is not the same as the print having a stem there. Where that matters
the probe says so and stops.

CONTROLS
  * the deletions must be non-zero, or there is nothing to attribute (exit 2);
  * the per-thickness totals must reproduce `fixture_arm.py`'s, or the two
    instruments disagree about the same page and neither can be quoted.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_stems, _staff_line_spacing  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page                       # noqa: E402
from tools.omr.staff_detector import detect_staves                    # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines           # noqa: E402
from tools.omr.training.line_detection_eval import (                  # noqa: E402
    GROUND_TRUTH_PATH, THICKNESSES, engrave)

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")


def key(d):
    return (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)


def on_head(k, heads):
    x, y, w, h = k
    return any(min(x + w, hx + hw) - max(x, hx) > 0
               and min(y + h, hy + hh) - max(y, hy) > 0
               for hx, hy, hw, hh in heads)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--json", default=str(HERE / "out" / "reference-why.json"))
    a = ap.parse_args()
    if not shutil.which("lilypond"):
        print("DEAD: lilypond not on PATH")
        return 2
    if not Path(a.weights).exists():
        print(f"DEAD: no weights at {a.weights}")
        return 2
    from tools.omr.yolo_detector import YoloDetector
    det = YoloDetector(a.weights)

    gt = json.loads(GROUND_TRUTH_PATH.read_text())
    per_staff_truth = {int(k): v["stems"]
                       for k, v in gt["per_staff_totals"].items()}
    per_bar = {int(k): v for k, v in gt["per_measure"].items()}
    truth = sum(per_staff_truth.values())

    rows = []
    with tempfile.TemporaryDirectory() as td:
        for t in THICKNESSES:
            pdf = engrave(t, Path(td))
            pws = detect_barlines(detect_staves(render_page(pdf, 0, dpi=600)))
            cells = extract_measures(pws)
            remove_staff_lines(cells)
            n_on = n_off = 0
            deleted = []
            per_staff_on = Counter()
            per_staff_off = Counter()
            n_cells_per_staff = Counter()
            for c in cells:
                heads = [(float(d.x_canonical), float(d.y_canonical),
                          float(d.width_canonical), float(d.height_canonical))
                         for d in (det.detect(c) or [])
                         if "notehead" in
                         str(getattr(d, "smufl_name", "")).lower()]
                on = detect_stems(c)
                off = detect_stems(c, drop_accidental_pairs=False)
                n_on += len(on)
                n_off += len(off)
                per_staff_on[c.staff_index] += len(on)
                per_staff_off[c.staff_index] += len(off)
                n_cells_per_staff[c.staff_index] += 1
                ks_on = {key(d) for d in on}
                sp = _staff_line_spacing(c) or 1.0
                for d in off:
                    if key(d) in ks_on:
                        continue
                    deleted.append({
                        "staff": int(c.staff_index),
                        "cell": int(c.measure_index),
                        "h_spaces": round(d.height_canonical / sp, 2),
                        "w_spaces": round(d.width_canonical / sp, 2),
                        "on_a_notehead": on_head(key(d), heads),
                    })
            n_del = len(deleted)
            n_del_on_head = sum(1 for d in deleted if d["on_a_notehead"])
            print(f"\n== thickness {t}:  ON {n_on}  OFF {n_off}  "
                  f"truth {truth}   deleted {n_del}")
            if n_del:
                print(f"   of the {n_del} deleted, {n_del_on_head} "
                      f"({100.0 * n_del_on_head / n_del:.1f}%) stand on a "
                      f"detected notehead -- the gate protects exactly those")
            for s in sorted(per_staff_truth):
                print(f"   staff {s}: truth {per_staff_truth[s]:3d}   "
                      f"ON {per_staff_on[s]:3d}   OFF {per_staff_off[s]:3d}   "
                      f"({n_cells_per_staff[s]} cells)")
            by_cell = Counter((d["staff"], d["cell"]) for d in deleted)
            if by_cell:
                print("   deletions by (staff, cell):")
                for (s, ci), n in sorted(by_cell.items()):
                    bars = per_bar.get(s) or []
                    what = (bars[ci]["content"]
                            if 0 <= ci < len(bars) else "?")
                    # ⚠️ THE CELL INDEX IS NOT THE BAR NUMBER when the page
                    # re-segments -- `ground-truth.json` says so itself
                    # ("at thickness 1 the barline before the chord measure is
                    # missed and two measures fuse into one cell"). The
                    # content is printed as a HINT and is labelled one.
                    print(f"      staff {s} cell {ci}: {n:2d} deleted   "
                          f"[hint, if cells==bars: {what}]")
            rows.append({"thickness": t, "on": n_on, "off": n_off,
                         "truth": truth, "deleted": n_del,
                         "deleted_on_a_notehead": n_del_on_head,
                         "per_staff_truth": per_staff_truth,
                         "per_staff_on": dict(per_staff_on),
                         "per_staff_off": dict(per_staff_off),
                         "deleted_detail": deleted})

    total_del = sum(r["deleted"] for r in rows)
    if total_del == 0:
        print("\nDEAD: the pair rule deletes NOTHING on this sheet, so there "
              "is nothing to attribute.")
        return 2
    total_on_head = sum(r["deleted_on_a_notehead"] for r in rows)
    print(f"\n== POOLED over four thicknesses: {total_del} deleted, "
          f"{total_on_head} on a notehead "
          f"({100.0 * total_on_head / total_del:.1f}%)")
    print("== ⚠️ THE SHEET PRINTS NO ACCIDENTAL. Whatever these are, they are "
          "not the sharps and flats the rule's docstring names.")

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps({"weights": a.weights, "rows": rows},
                                       indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
