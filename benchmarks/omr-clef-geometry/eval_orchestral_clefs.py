"""Clef-locator PRECISION on degraded orchestral prints.

`clef_ground_truth_eval.py` scores Nottebohm — vocal exercises, C clefs
everywhere, the material the locator was built for. It says nothing about
orchestral scores, which are what most real work is, and where the locator
behaves differently: the header holds a bracket, instrument names and stacked
part numbers, and two thirds of the staves carry the G and F clefs the locator
is supposed to decline.

There is already hand-read ground truth for two such pages, and it is sitting
in the key-signature benchmark: `benchmarks/omr-key-signature/ground_truth.json`
records each staff's `clef` alongside its key signature, read off the page by
eye. This scores the locator against that, so orchestral precision is a number
rather than an impression.

    python3 benchmarks/omr-clef-geometry/eval_orchestral_clefs.py

Precision only — it counts what the locator SAID and whether it was right. It
deliberately does not report recall against the 42 staves, because the locator
declines G and F clefs by design and a "miss" on a treble staff is correct
behaviour, not lost coverage. Use `probe_clef_rejection.py` for coverage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import locate_clef  # noqa: E402
from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402

GROUND_TRUTH = REPO / "benchmarks" / "omr-key-signature" / "ground_truth.json"
ORCHESTRAL = ("beet5-p2", "pastoral-p2")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--page", default=None, help="only this ground-truth page id")
    args = ap.parse_args()

    truth_file = json.loads(GROUND_TRUTH.read_text())
    pages = [
        p for p in truth_file["pages"]
        if p["id"] in ORCHESTRAL and args.page in (None, p["id"])
    ]
    correct = wrong = 0
    for page in pages:
        pdf = Path(page["pdf"])
        pdf = pdf if pdf.is_absolute() else REPO / pdf
        print(f"\n=== {page['id']}")
        if not pdf.exists():
            print(f"  SKIPPED: PDF not on this machine ({pdf})")
            continue
        truth = {s["ordinal"]: s["clef"] for s in page["staves"]}
        rendered = render_page(pdf, page["page_index"], dpi=page["dpi"])
        pws = detect_barlines(detect_staves(rendered))
        cells = header_cells_for_page(pws)
        spoke = False
        for system_index in sorted({s.system_index for s in pws.staves}):
            staves = sorted(
                (s for s in pws.staves if s.system_index == system_index),
                key=lambda s: s.top_y,
            )
            for ordinal, staff in enumerate(staves):
                cell = cells.get(staff.staff_index)
                found = locate_clef(cell) if cell is not None else None
                if found is None:
                    continue
                spoke = True
                expected = truth.get(ordinal, "?")
                good = found.read.name == expected
                correct += good
                wrong += not good
                print(f"  sys{system_index} ord{ordinal}: expected {expected:<7} "
                      f"located {found.read.name:<7} "
                      f"{'ok' if good else 'WRONG'}   symmetry={found.symmetry}")
        if not spoke:
            print("  the locator declined every staff")

    total = correct + wrong
    if not total:
        print("\n  nothing located — no precision to report")
        return 0
    print(f"\n  located {total} staves: {correct} correct, {wrong} wrong "
          f"({100.0 * correct / total:.0f}% precision)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
