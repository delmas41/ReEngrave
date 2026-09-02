"""The header meter reader over eleven sources instead of five.

`benchmarks/omr-timesig-2026-08/sweep_time_signatures.py` is the original and
still runs; this does not replace it. It adds the pages the 08 corpus could not
contain, and it can run the 08 cases alongside so one number covers both
(`--with-08`, the default).

What is new, and why each page is here, is in `corpus.json` next to this file.
The short version: seven pages that print a real **cut common**, which is the
evidence the 08 work said it did not have when it withheld that template; one
page printing **4/8**, the only meter in the whole dossier set the locator
cannot search for; and 3/4, 6/4 and four publishers the 08 corpus lacks.

    python3 benchmarks/omr-timesig-2026-09/sweep_widened.py
    python3 benchmarks/omr-timesig-2026-09/sweep_widened.py --per-staff --min-score 0
    python3 benchmarks/omr-timesig-2026-09/sweep_widened.py --add-meters 4/8
    python3 benchmarks/omr-timesig-2026-09/sweep_widened.py --add-meters 'C|'

⚠️ **A wrong reading refuses the change that produced it.** A meter is believed
by every bar of its page, so one wrong answer costs more than any number of
abstentions gains — that is the trade the 08 work priced and took, twice. The
summary line prints `wrong` first for that reason.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.measure_extractor import detect_barlines  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import (  # noqa: E402
    header_cells_for_page,
    header_windows_for_page,
)
from tools.omr.time_signature_locator import (  # noqa: E402
    DEFAULT_LOCATOR_CONFIG,
    DEFAULT_METERS,
    locate_time_signature,
    vote_system_time_signature,
)

BENCH = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[2]
CORPUS = json.loads((BENCH / "corpus.json").read_text())
LIB = Path(CORPUS["library_root"])

#: The 08 corpus, re-declared rather than imported, because its module runs its
#: own `main()` on import of `CASES` only by accident of layout and because the
#: paths there are absolute to a machine. Truth is unchanged from that file.
GRADUS = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
BEET5_SCAN = GRADUS / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf"
FIXTURES = REPO / "benchmarks" / "omr-orchestral-e2e" / "fixtures"
PHASE4 = REPO / "benchmarks" / "omr-phase4-extension" / "output"
CASES_08 = [
    ("beet5-scan-p1", BEET5_SCAN, 1, ["2/4"]),
    ("beet5-scan-p2", BEET5_SCAN, 2, [None, None]),
    ("beet5-scan-p3", BEET5_SCAN, 3, [None, None]),
    ("beet5-scan-p4", BEET5_SCAN, 4, [None, None]),
    ("beet5-scan-p5", BEET5_SCAN, 5, [None, None]),
    ("beet5-scan-p6", BEET5_SCAN, 6, [None, None]),
    ("e2e-beethoven", FIXTURES / "beethoven-sym5-mvt1.pdf", 0, ["2/4"]),
    ("e2e-brahms", FIXTURES / "brahms-sym1-mvt1.pdf", 0, ["6/8"]),
    ("e2e-mahler", FIXTURES / "mahler-sym5-mvt1.pdf", 0, ["2/2"]),
    ("ravel-bolero", PHASE4 / "ravel-bolero.pdf", 0, ["C"]),
    ("handel-reduction", PHASE4 / "handel-reduction.pdf", 0, ["C"]),
    ("bach-wtc", PHASE4 / "bach-wtc.pdf", 0, ["C"]),
    ("wtc-book-p2", GRADUS / "PDF Scores" /
     "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 2,
     ["C", None, None, None, None, None]),
    ("wtc-book-p3", GRADUS / "PDF Scores" /
     "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 3,
     [None, None, None, None, None, None]),
]

#: Meters that can be named on `--add-meters` but are not in `DEFAULT_METERS`.
#: The letter forms carry the same `(numerator, denominator)` as their digit
#: spelling and are separated by `raw`, exactly as `C` already is.
ADDABLE = {
    "4/8": (4, 8, "4/8"),
    "2/8": (2, 8, "2/8"),
    "4/16": (4, 16, "4/16"),
    "C|": (2, 2, "C|"),
}


def cases_09() -> list[tuple[str, Path, int, list]]:
    return [(c["label"], LIB / c["pdf"], c["page"], c["expected"])
            for c in CORPUS["cases"]]


def run_case(pdf: Path, page_index: int, min_score: float | None, config):
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
            locate_time_signature(cells[i], config=config, min_score=min_score)
            if i in cells else None
            for i in indices
        ]
        meter = vote_system_time_signature(reads, n_staves=len(indices), config=config)
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
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--per-staff", action="store_true")
    ap.add_argument("--min-score", type=float, default=None)
    ap.add_argument("--add-meters", default="",
                    help="comma-separated raws to add to the candidate list, "
                         f"from {sorted(ADDABLE)}")
    ap.add_argument("--only-09", action="store_true",
                    help="skip the 08 corpus (it is included by default)")
    ap.add_argument("--only", default="", help="comma-separated case labels")
    ap.add_argument("--out", default="sweep.json")
    args = ap.parse_args()

    meters = DEFAULT_METERS
    if args.add_meters:
        extra = tuple(ADDABLE[m.strip()] for m in args.add_meters.split(","))
        meters = DEFAULT_METERS + extra
    config = replace(DEFAULT_LOCATOR_CONFIG, meters=meters)

    cases = cases_09() if args.only_09 else CASES_08 + cases_09()
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        cases = [c for c in cases if c[0] in keep]

    report, right, wrong, missed, silence = [], 0, 0, 0, 0
    for label, pdf, page_index, expected in cases:
        if not Path(pdf).is_file():
            print(f"{label:<18} MISSING {pdf}")
            continue
        t0 = time.perf_counter()
        systems = run_case(Path(pdf), page_index, args.min_score, config)
        for i, system in enumerate(systems):
            want = expected[i] if i < len(expected) else None
            got = system["meter"]["raw"] if system["meter"] else None
            if want is None and got is None:
                verdict, silence = "silent  ", silence + 1
            elif want is not None and got == want:
                verdict, right = "OK      ", right + 1
            elif got is None:
                verdict, missed = "MISSED  ", missed + 1
            else:
                verdict, wrong = "WRONG   ", wrong + 1
            votes = (f"{system['meter']['votes']}/{system['meter']['voters']}"
                     if system["meter"] else f"-/{system['n_staves']}")
            score = system["meter"]["median_score"] if system["meter"] else ""
            print(f"{label:<18} sys{system['system']}  {verdict} "
                  f"want={str(want):<5} got={str(got):<5} votes={votes:<7} {score}")
            if args.per_staff:
                for entry in system["per_staff"]:
                    if entry:
                        print(f"      staff {entry['staff']:2d}  {entry['raw']:<5} "
                              f"{entry['score']}")
        report.append({"case": label, "expected": expected, "systems": systems,
                       "seconds": round(time.perf_counter() - t0, 1)})

    print(f"\nWRONG {wrong}   correct {right}   missed {missed}   "
          f"correct silences {silence}"
          + (f"   [+{args.add_meters}]" if args.add_meters else ""))
    out = BENCH / args.out
    out.write_text(json.dumps(
        {"add_meters": args.add_meters, "min_score": args.min_score,
         "totals": {"wrong": wrong, "correct": right, "missed": missed,
                    "correct_silences": silence},
         "cases": report}, indent=2) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
