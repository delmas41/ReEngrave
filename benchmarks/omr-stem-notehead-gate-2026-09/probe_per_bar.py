"""THE REFERENCE SHEET'S TRUTH IS PER BAR, AND THE PAGE TOTAL HIDES THE ERROR.

`fixture_arm.py` scores the sheet the way `_drop_paired_strokes`' docstring
does — a WHOLE-PAGE total against 48 — and by that reading the gate looks
disastrous (summed |error| 3 -> 27). `probe_reference_sheet.py` then found
that every deletion on the sheet lands in ONE cell of staff 0.

`ground-truth.json` has carried a PER-BAR truth all along (`per_measure`),
and `line_detection_eval.score_pdf` deliberately does not use it: *"measure
segmentation is not stable across line thicknesses"*. That caveat is real and
it is CHECKABLE rather than permanent — this probe scores per bar only at a
thickness where the page cuts exactly as many cells as the sheet has bars,
ON BOTH STAVES, and REFUSES at every other thickness by name.

⚠️⚠️ AND IT CARRIES ITS OWN CORRECTION. On the chord bar the gated arm's
count EQUALS the truth, and that equality is a COINCIDENCE OF COMPOSITION,
not four correct stems: the four strokes form TWO x-clusters of two, so two
chords contribute two strokes each and two chords contribute none. Scoring
that bar by COUNT alone would report the gate as exactly right. The probe
therefore also reports HOW MANY CHORDS CARRY ANY STROKE, which is the
statement the geometry supports.

CONTROLS
  * REACH: the number of thicknesses where cells==bars on both staves. Zero
    is DEAD (exit 2) and the caveat stands un-lifted.
  * POSITIVE: the three arms must differ on some bar.
  * The x-cluster composition check is printed whether or not it is
    comfortable.
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

from tools.omr.line_detection import detect_stems, _staff_line_spacing  # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page                       # noqa: E402
from tools.omr.staff_detector import detect_staves                    # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines           # noqa: E402
from tools.omr.training.line_detection_eval import (                  # noqa: E402
    GROUND_TRUTH_PATH, THICKNESSES, engrave)

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt")

#: Two strokes are the SAME printed object for the composition count when
#: their centres are this close, in staff spaces. ⚠️ NOT A NEW DETECTION
#: CONSTANT and it decides nothing in the pipeline: it exists only so a
#: reader of this probe can see that four strokes are two objects. It is the
#: pair rule's OWN window (`accidental_pair_gap_lines`), imported in spirit
#: rather than invented — using a different number here would let the probe
#: disagree with the rule about what "adjacent" means.
CLUSTER_SPACES = 0.9


def heads_of(det, c):
    return [(float(d.x_canonical), float(d.y_canonical),
             float(d.width_canonical), float(d.height_canonical))
            for d in (det.detect(c) or [])
            if "notehead" in str(getattr(d, "smufl_name", "")).lower()]


def x_clusters(strokes, sp):
    """How many distinct printed objects these strokes are, by x proximity."""
    xs = sorted((s.x_canonical + s.width_canonical / 2.0) / sp
                for s in strokes)
    n = 0
    prev = None
    for x in xs:
        if prev is None or x - prev > CLUSTER_SPACES:
            n += 1
        prev = x
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default=WEIGHTS)
    ap.add_argument("--json", default=str(HERE / "out" / "per-bar.json"))
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
    per_bar = {int(k): v for k, v in gt["per_measure"].items()}
    n_bars = {s: len(v) for s, v in per_bar.items()}

    scored, skipped, out_rows = [], [], []
    with tempfile.TemporaryDirectory() as td:
        for t in THICKNESSES:
            pdf = engrave(t, Path(td))
            pws = detect_barlines(detect_staves(render_page(pdf, 0, dpi=600)))
            cells = extract_measures(pws)
            remove_staff_lines(cells)
            got = {}
            for c in cells:
                got.setdefault(c.staff_index, []).append(c)
            # ⚠️ THE REFUSAL, BY NAME. Per-bar scoring is only valid where the
            # cut agrees with the sheet; anywhere else the cell index is not
            # the bar number and the comparison would be nonsense.
            if set(got) != set(n_bars) or any(
                    len(got[s]) != n_bars[s] for s in n_bars):
                shape = {s: len(v) for s, v in sorted(got.items())}
                print(f"== thickness {t}: REFUSED -- the page cuts {shape} "
                      f"cells against the sheet's {n_bars} bars, so a cell "
                      f"index is not a bar number here.")
                skipped.append({"thickness": t, "cells": shape})
                continue
            scored.append(t)
            err = {"on": 0, "off": 0, "gated": 0}
            rows = []
            print(f"\n== thickness {t}: cells == bars on both staves, "
                  f"per-bar truth is usable")
            print(f"{'staff':>5} {'bar':>4} {'content':>36} {'truth':>5} "
                  f"{'ON':>4} {'OFF':>4} {'GATED':>5}")
            for c in sorted(cells, key=lambda c: (c.staff_index,
                                                  c.measure_index)):
                b = per_bar[c.staff_index][c.measure_index]
                heads = heads_of(det, c)
                on = detect_stems(c)
                off = detect_stems(c, drop_accidental_pairs=False)
                gated = detect_stems(c, noteheads=heads,
                                     enable_notehead_gate=True)
                sp = _staff_line_spacing(c) or 1.0
                counts = {"on": len(on), "off": len(off), "gated": len(gated)}
                for k, v in counts.items():
                    err[k] += abs(v - b["stems"])
                rows.append({
                    "staff": c.staff_index, "bar": c.measure_index + 1,
                    "content": b["content"], "truth": b["stems"], **counts,
                    "x_clusters_on": x_clusters(on, sp),
                    "x_clusters_off": x_clusters(off, sp),
                    "x_clusters_gated": x_clusters(gated, sp),
                })
                print(f"{c.staff_index:>5} {c.measure_index + 1:>4} "
                      f"{b['content'][:36]:>36} {b['stems']:>5} "
                      f"{counts['on']:>4} {counts['off']:>4} "
                      f"{counts['gated']:>5}")
            print(f"   summed |error| per bar   ON {err['on']:3d}   "
                  f"OFF {err['off']:3d}   GATED {err['gated']:3d}")
            emptied = [r for r in rows if r["truth"] > 0 and r["on"] == 0]
            for r in emptied:
                print(f"   ⚠️ the shipped rule EMPTIES staff {r['staff']} "
                      f"bar {r['bar']} ({r['content']}): truth "
                      f"{r['truth']}, ON 0, OFF {r['off']}, "
                      f"GATED {r['gated']}")
                print(f"      ⚠️ COMPOSITION: those strokes are "
                      f"{r['x_clusters_off']} distinct x-cluster(s), not "
                      f"{r['off']} -- so a COUNT equal to the truth here "
                      f"would be a coincidence, and what the geometry "
                      f"supports is 'strokes on {r['x_clusters_gated']} of "
                      f"{r['truth']} printed objects' against ON's "
                      f"{r['x_clusters_on']}.")
            out_rows.append({"thickness": t, "summed_abs_error": err,
                             "rows": rows})

    print(f"\n== REACH: {len(scored)} of {len(THICKNESSES)} thicknesses "
          f"scoreable per bar {scored}; {len(skipped)} refused")
    if not scored:
        print("DEAD: no thickness cuts cells==bars, so the ground truth's own "
              "caveat stands and nothing per-bar can be said.")
        return 2
    allrows = [r for g in out_rows for r in g["rows"]]
    if all(r["on"] == r["off"] == r["gated"] for r in allrows):
        print("DEAD: POSITIVE CONTROL FAILED -- the three arms agree on every "
              "bar.")
        return 2

    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(
        {"weights": a.weights, "scored": out_rows, "refused": skipped},
        indent=1))
    print(f"wrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
