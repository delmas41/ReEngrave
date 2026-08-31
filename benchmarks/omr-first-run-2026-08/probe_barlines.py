"""Barline recall and precision on pages whose barlines are known.

Truth comes from `probe_page_measures.py`'s column test, run on every staff of
the page that rests for its whole width — see that file for why a tacet staff
gives an exact answer and a playing one does not, and for the time signature
that fooled the first version of it.

Reported as barlines rather than measures because that is what the detector
decides, and because a missed barline in the middle costs two measures while a
missed final one costs one.

    python3 benchmarks/omr-first-run-2026-08/probe_barlines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.measure_extractor import detect_barlines
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

GRADUS = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
BEET5 = GRADUS / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"
REPO = Path(__file__).resolve().parents[2]

#: (label, pdf, page, truth barline x's) — hand-verified, see the module doc.
#: Only page 1 has tacet staves across the full width, so only page 1 has exact
#: truth; the rest are watched for COUNT stability, which is what a regression
#: in the vote or the connectivity probe would move.
CASES = [
    ("beet5-p1", BEET5, 1,
     [667, 1000, 1068, 1200, 1264, 1336, 1461, 1587, 1712, 1782, 1907, 2048,
      2166, 2232, 2354, 2469, 2608]),
    ("beet5-p2", BEET5, 2, None),
    ("beet5-p3", BEET5, 3, None),
    ("beet5-p4", BEET5, 4, None),
    ("wtc-p2", GRADUS / "PDF Scores" /
     "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 2, None),
    ("e2e-beethoven", REPO / "benchmarks/omr-orchestral-e2e/fixtures/beethoven-sym5-mvt1.pdf", 0, None),
    ("e2e-brahms", REPO / "benchmarks/omr-orchestral-e2e/fixtures/brahms-sym1-mvt1.pdf", 0, None),
]
TOL = 25  # px at 600 dpi: a leaning barline's mean sits mid-system


def main() -> None:
    for label, pdf, page_index, truth in CASES:
        if not pdf.is_file():
            print(f"{label:<15} MISSING {pdf}")
            continue
        pws = detect_barlines(detect_staves(render_page(pdf, page_index, dpi=600)))
        by_system: dict[int, list[int]] = {}
        for barline in pws.barlines:
            by_system.setdefault(barline.system_index, []).append(barline.x)
        got = sorted(x for xs in by_system.values() for x in xs)
        if truth is None:
            counts = {k: len(v) for k, v in sorted(by_system.items())}
            print(f"{label:<15} {len(got):>3} barlines  per system {counts}")
            continue
        hit = [t for t in truth if any(abs(g - t) <= TOL for g in got)]
        false = [g for g in got if not any(abs(g - t) <= TOL for t in truth)]
        print(f"{label:<15} {len(hit)}/{len(truth)} found, {len(false)} false"
              f"  -> {len(got) - 1} measures (truth {len(truth) - 1})")
        if false:
            print(f"{'':<15} false at {false}")


if __name__ == "__main__":
    main()
