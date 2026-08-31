"""Does the header meter reader answer, and is it right — across print styles.

The one thing this must not do is trade a silence for a confident wrong answer.
Before the reader existed, page 1 of the Beethoven 5 scan reported common time
on a 2/4 movement, propagated from five barline fragments read as the digit 4;
a reader that produced 4/4 more often would look like an improvement on any
metric that only counts answers.

So the corpus is deliberately half NEGATIVES — pages that print no time
signature at all, which is every system after the first in almost any score.
On those the only correct behaviour is to abstain, and a wrong meter costs more
than no meter.

    python3 benchmarks/omr-timesig-2026-08/sweep_time_signatures.py
    python3 benchmarks/omr-timesig-2026-08/sweep_time_signatures.py --per-staff

Truth is hand-read off each page. Where a page's systems differ — the first
system prints the meter, the second does not — the expectation is per system,
which is why the report is per system rather than per page.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.measure_extractor import detect_barlines
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr.staff_header import header_cells_for_page, header_windows_for_page
from tools.omr.time_signature_locator import (
    DEFAULT_LOCATOR_CONFIG,
    locate_time_signature,
    vote_system_time_signature,
)

BENCH = Path(__file__).resolve().parent
GRADUS = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
REPO = Path(__file__).resolve().parents[2]
BEET5_SCAN = GRADUS / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"
FIXTURES = REPO / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
PHASE4 = REPO / "benchmarks" / "omr-phase4-extension" / "output"

#: (label, pdf, page_index, per-system expected meter — None where the system
#: prints none). Hand-read from the page.
CASES = [
    # Scanned, 19th-century type. Page 1 prints 2/4 on all twelve staves; every
    # later page prints none, and both of its systems must stay silent.
    ("beet5-scan-p1", BEET5_SCAN, 1, ["2/4"]),
    ("beet5-scan-p2", BEET5_SCAN, 2, [None, None]),
    ("beet5-scan-p3", BEET5_SCAN, 3, [None, None]),
    ("beet5-scan-p4", BEET5_SCAN, 4, [None, None]),
    ("beet5-scan-p5", BEET5_SCAN, 5, [None, None]),
    ("beet5-scan-p6", BEET5_SCAN, 6, [None, None]),
    # Engraved by LilyPond — a different font (Feta) from the Bravura templates,
    # which is the point of including them.
    ("e2e-beethoven", FIXTURES / "beethoven-sym5-mvt1.pdf", 0, ["2/4"]),
    ("e2e-brahms", FIXTURES / "brahms-sym1-mvt1.pdf", 0, ["6/8"]),
    ("e2e-mahler", FIXTURES / "mahler-sym5-mvt1.pdf", 0, ["2/2"]),
    # Both of these print the common-time C, which the symbol library has no
    # template for. The expected result is an ABSTENTION, not a reading — and
    # they earn their place by proving it is one. Labelling them 3/4 and 4/4
    # from memory of the works, as this file first did, scored the correct
    # abstention as a miss; the pages say C.
    ("ravel-bolero", PHASE4 / "ravel-bolero.pdf", 0, ["C"]),
    ("handel-reduction", PHASE4 / "handel-reduction.pdf", 0, ["C"]),
]


def run_case(pdf: Path, page_index: int, min_score: float | None):
    page = render_page(pdf, page_index, dpi=600)
    pws = detect_barlines(detect_staves(page))
    cells = header_cells_for_page(pws, windows=header_windows_for_page(pws))
    by_system: dict[int, list[int]] = {}
    for staff in pws.staves:
        by_system.setdefault(staff.system_index, []).append(staff.staff_index)
    out = []
    for system_index in sorted(by_system):
        indices = sorted(by_system[system_index])
        reads = [
            locate_time_signature(cells[i], min_score=min_score) if i in cells else None
            for i in indices
        ]
        meter = vote_system_time_signature(
            [r for r in reads], n_staves=len(indices), config=DEFAULT_LOCATOR_CONFIG
        )
        out.append({
            "system": system_index,
            "n_staves": len(indices),
            "meter": meter,
            "per_staff": [
                None if r is None else
                {"staff": i, "raw": r.raw, "score": round(r.score, 3)}
                for i, r in zip(indices, reads)
            ],
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-staff", action="store_true",
                    help="print every staff's reading, not just the system vote")
    ap.add_argument("--min-score", type=float, default=None,
                    help="override the locator threshold (0.0 shows near-misses)")
    args = ap.parse_args()

    report, right, wrong, missed, correct_silence = [], 0, 0, 0, 0
    for label, pdf, page_index, expected in CASES:
        if not pdf.is_file():
            print(f"{label:<18} MISSING {pdf}")
            continue
        systems = run_case(pdf, page_index, args.min_score)
        for i, system in enumerate(systems):
            want = expected[i] if i < len(expected) else None
            got = system["meter"]["raw"] if system["meter"] else None
            if want == "C":
                # No common-time template exists, so silence is the right
                # answer and any reading is a false one.
                verdict = "silent-C" if got is None else "WRONG   "
                if got is None:
                    correct_silence += 1
                else:
                    wrong += 1
            elif want is None and got is None:
                verdict, correct_silence = "silent  ", correct_silence + 1
            elif want is not None and got == want:
                verdict, right = "OK      ", right + 1
            elif got is None:
                verdict, missed = "MISSED  ", missed + 1
            else:
                verdict, wrong = "WRONG   ", wrong + 1
            votes = f"{system['meter']['votes']}/{system['meter']['voters']}" \
                if system["meter"] else f"-/{system['n_staves']}"
            score = system["meter"]["median_score"] if system["meter"] else ""
            print(f"{label:<18} sys{system['system']}  {verdict} "
                  f"want={str(want):<5} got={str(got):<5} votes={votes:<6} {score}")
            if args.per_staff:
                for entry in system["per_staff"]:
                    if entry:
                        print(f"      staff {entry['staff']:2d}  {entry['raw']:<5} "
                              f"{entry['score']}")
        report.append({"case": label, "expected": expected, "systems": systems})

    print(f"\ncorrect {right}   wrong {wrong}   missed {missed}   "
          f"correct silences {correct_silence}")
    out = BENCH / "sweep.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
