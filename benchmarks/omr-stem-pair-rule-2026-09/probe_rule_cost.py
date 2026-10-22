"""WHAT THE PAIR RULE IS WORTH ON ITS OWN TRUTH SET -- so "turn it off" is priced.

`probe_who_is_the_partner.py` measures that on Litolff Beethoven 5 pp.1-4 the
rule's dominant victim is a stroke whose partner ALSO carries a notehead: two
genuine stems standing within 0.9 staff spaces, deleting each other. That is a
reason to change the rule; it is NOT on its own a reason to remove it, because
the rule was shipped against a hand count and this document is not in it.

So: re-run that hand count with the rule ON and OFF.
`benchmarks/omr-phase4-lines/hand-labeled-stems.json`, 15 cells over La Mer,
Bolero, Mahler 5 and WTC (one `null`, excluded by the labeler). The counting
rule is the labeler's own and matters here: **one stem per note OR CHORD** --
three noteheads sharing one stem count ONCE -- so a stem the rule eats costs 1
against this truth and N heads in the staged record. The two numbers are not
in the same currency and must not be differenced.

⚠️ THIS IS THE RULE'S OWN EVIDENCE, RE-RUN, NOT NEW EVIDENCE ABOUT IT. It says
what disabling the rule costs where it was justified; it says nothing about
Litolff Beethoven 5, which is the whole point -- that plate is not in this set.

POSITIVE CONTROL: the two arms must differ on at least one cell. They are the
same harness with one keyword changed, and a keyword that failed to reach
`detect_stems` would report a clean, believable "no cost".
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.line_detection import detect_stems                          # noqa: E402
from tools.omr.measure_extractor import detect_barlines, extract_measures  # noqa: E402
from tools.omr.preprocessing import render_page                            # noqa: E402
from tools.omr.staff_detector import detect_staves                         # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines                # noqa: E402
from tools.omr.training.line_detection_eval import (                       # noqa: E402
    HAND_STEMS_PATH, SCORE_ROOT, _resolve_cells)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "out" / "rule-cost.json"))
    a = ap.parse_args()

    data = json.loads(HAND_STEMS_PATH.read_text())
    pages, rows = {}, []
    on_err = off_err = 0
    n_scored = 0
    print(f"{'cell':>4} {'score':>14} {'truth':>6} {'ON':>5} {'OFF':>5} "
          f"{'|e| ON':>7} {'|e| OFF':>8}")
    for entry in data["cells"]:
        if entry["stems"] is None:
            continue
        spec = data["scores"][entry["score"]]
        pdf = SCORE_ROOT / spec.split(",")[0]
        if not pdf.exists():
            print(f"{entry['n']:>4} SKIP (missing {pdf.name})")
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
            print(f"{entry['n']:>4} {entry['score']:>14}  region not resolvable"
                  f" -- excluded")
            continue
        on = sum(len(detect_stems(c)) for c in group)
        off = sum(len(detect_stems(c, drop_accidental_pairs=False))
                  for c in group)
        t = entry["stems"]
        on_err += abs(on - t)
        off_err += abs(off - t)
        n_scored += 1
        rows.append({"n": entry["n"], "score": entry["score"], "truth": t,
                     "on": on, "off": off})
        print(f"{entry['n']:>4} {entry['score']:>14} {t:>6} {on:>5} {off:>5} "
              f"{abs(on - t):>7} {abs(off - t):>8}")

    print(f"\n== REACH: {n_scored} scoreable cells "
          f"({len(data['cells'])} labelled, 1 `null`)")
    if n_scored == 0:
        print("DEAD: nothing scored.")
        return 2
    print(f"   summed |error|, rule ON  (shipped): {on_err}")
    print(f"   summed |error|, rule OFF          : {off_err}")
    if on_err == off_err and all(r["on"] == r["off"] for r in rows):
        print("   DEAD: POSITIVE CONTROL FAILED -- the two arms are identical "
              "on every cell, so the keyword is not reaching detect_stems.")
        return 2
    worse = sum(1 for r in rows if abs(r["off"] - r["truth"])
                > abs(r["on"] - r["truth"]))
    better = sum(1 for r in rows if abs(r["off"] - r["truth"])
                 < abs(r["on"] - r["truth"]))
    print(f"   cells OFF is worse on: {worse}; better on: {better}; "
          f"equal: {n_scored - worse - better}")

    out = {"n_scored": n_scored, "summed_abs_error_on": on_err,
           "summed_abs_error_off": off_err, "cells_off_worse": worse,
           "cells_off_better": better, "rows": rows}
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_text(json.dumps(out, indent=1))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
