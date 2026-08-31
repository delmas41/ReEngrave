"""The precision half of the clef-locator measurement. Run it with the probe.

`probe_clef_rejection.py` counts how many header cells reach a clef and says
nothing about whether the clef is RIGHT. This says whether it is right, and
refuses to report a single combined number, because the two move independently
and the trade between them is not symmetric: a missed clef leaves a staff on
the default it already had, while a wrong one transposes every note on it. Any
change that buys coverage with a false positive has made the layer worse even
when the totals look better.

Three checks, in decreasing order of how much they should be trusted:

  reference  the engraved sheet from `reference-clefs.ly`, where the answer is
             known by construction. All five C clefs read exactly, treble and
             bass declined.
  piano      braced piano in fifteen keys from `piano-false-positives.ly`.
             There are no C clefs in it, so ANY read is a false positive. This
             stands in for the ten pages of scanned Bach WTC the earlier rounds
             used, which are not in the repo.
  orchestral a spot check on a scanned Beethoven 5, from
             `beethoven5-clef-spot-check.json`. The one corpus here that is a
             SCAN of an ORCHESTRAL score, and it earns its place: a change that
             grouped header ink vertically passed every other check and still
             read seventeen treble clefs as alto clefs on this material,
             because a thick scanned G clef fragments in ways a clean engraving
             never does. Skipped when the score, which lives in a gitignored
             data directory, is not present.

  sweep      `beethoven5-clef-sweep.json` — 91 staves of the same scan, being
             every staff the locator LOCATES a C clef on over pages 2-80 with
             clustering on, read by eye. Twenty-four of them are not C clefs
             (seventeen bass, seven treble) and are the reads a veto change
             exists to remove. Before this corpus the COST of a veto change was
             measurable on the four below and its BENEFIT was an anecdote, which
             is why every change to the F-clef veto stalled.

  coverage   the hand-read Nottebohm page. Real material, real engraving, but
             twelve staves — too small to steer by on its own, which is what
             the probe is for.

Both LilyPond sources have to be built first:

    cd benchmarks/omr-clef-geometry
    lilypond reference-clefs.ly piano-false-positives.ly
    python3 check_clef_precision.py --nottebohm /path/to/Nottebohm-...pdf

The reference sheet is read at 600 dpi, the pipeline CLI's default. At 300 the
engraved tenor clef's wings shrink until the F-clef dot veto mistakes them for
dots and declines it — a resolution artefact of that one glyph, not a
regression, but it means the two resolutions disagree and the check has to name
which one it is asserting.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from tools.omr.clef_locator import locate_clef  # noqa: E402
from tools.omr.measure_extractor import (  # noqa: E402
    detect_barlines,
    extract_measures,
    resegment_fused_measures,
)
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.staff_header import header_cells_for_page  # noqa: E402
from tools.omr.staff_line_removal import remove_staff_lines  # noqa: E402

C_CLEFS = {"soprano", "mezzosoprano", "alto", "tenor", "baritone"}
REFERENCE_ORDER = [
    "soprano", "mezzosoprano", "alto", "tenor", "baritone", "treble", "bass",
]


def read_page(pdf: Path, page_index: int, dpi: int) -> list[tuple[int, str | None]]:
    """What the CV locator alone makes of every staff on one page, top to
    bottom. Phase 1 plus the locator, no YOLO — so the number moves when the
    locator moves and not when the detector does.
    """
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_barlines(detect_staves(page))
    cells = resegment_fused_measures(pws, extract_measures(pws))
    remove_staff_lines(cells)
    headers = header_cells_for_page(pws)
    out = []
    for staff in sorted(pws.staves, key=lambda s: s.top_y):
        cell = headers.get(staff.staff_index)
        found = locate_clef(cell) if cell is not None else None
        out.append((staff.staff_index, found.read.name if found else None))
    return out


def check_reference(pdf: Path, dpi: int) -> tuple[int, int]:
    print(f"\nreference sheet ({pdf.name}, {dpi} dpi) — answers known by construction")
    exact = wrong = 0
    rows = read_page(pdf, 0, dpi)
    for i, expected in enumerate(REFERENCE_ORDER):
        got = rows[i][1] if i < len(rows) else None
        if expected in C_CLEFS:
            if got == expected:
                exact += 1
            elif got is None:
                print(f"    MISS            {expected}: declined")
            else:
                wrong += 1
                print(f"    FALSE POSITIVE  {expected}: read {got}")
        elif got is not None:
            wrong += 1
            print(f"    FALSE POSITIVE  {expected}: read {got}")
    print(f"  {exact}/5 C clefs exact, treble and bass declined"
          f"   false positives {wrong}")
    return exact, wrong


def check_piano(pdf: Path, dpis: tuple[int, ...]) -> tuple[int, int]:
    print(f"\npiano ({pdf.name}) — no C clefs exist, so any read is a false positive")
    import fitz

    n_pages = fitz.open(str(pdf)).page_count
    staves = wrong = 0
    for dpi in dpis:
        for p in range(n_pages):
            for staff_index, got in read_page(pdf, p, dpi):
                staves += 1
                if got is not None:
                    wrong += 1
                    print(f"    FALSE POSITIVE  p{p} staff {staff_index} "
                          f"@{dpi}dpi: read {got}")
    print(f"  {staves} staves read   false positives {wrong}")
    return staves, wrong


def check_orchestral(pdf: Path, spec_path: Path, dpi: int,
                     title: str = "orchestral spot check") -> tuple[int, int, int]:
    spec = json.loads(spec_path.read_text())
    print(f"\n{title} ({pdf.name}) — {spec['source']}")
    by_page: dict[int, list[dict]] = {}
    for row in spec["staves"]:
        by_page.setdefault(row["page"], []).append(row)
    found = missed = wrong = 0
    for page_index in sorted(by_page):
        read = dict(read_page(pdf, page_index, dpi))
        for row in by_page[page_index]:
            got = read.get(row["staff"])
            if row["c_clef"]:
                if got is not None:
                    found += 1
                else:
                    missed += 1
                    print(f"    MISS            p{page_index} staff {row['staff']}: "
                          f"declined a real C clef")
            elif got is not None:
                # A staff main already misreads is the baseline, not a
                # regression — printed, but it must not mask a new one.
                tag = "KNOWN       " if row.get("pre_existing") else "FALSE POSITIVE"
                if not row.get("pre_existing"):
                    wrong += 1
                print(f"    {tag}  p{page_index} staff {row['staff']}: "
                      f"read {got} — {row.get('note', 'not a C clef')}")
    print(f"  {found} of {found + missed} known C clefs still read"
          f"   NEW false positives {wrong}")
    return found, missed, wrong


def check_coverage(pdf: Path, truth_path: Path, dpi: int) -> tuple[int, int, int]:
    truth = json.loads(truth_path.read_text())
    print(f"\ncoverage ({pdf.name} page {truth['pdf_page_index']}) — hand-read truth")
    rows = read_page(pdf, truth["pdf_page_index"], dpi)
    expected = truth["clefs"]
    n_c = sum(1 for e in expected if e["clef"] in C_CLEFS)
    right = wrong = 0
    for i, want in enumerate(expected):
        got = rows[i][1] if i < len(rows) else None
        if got is None:
            continue
        if got == want["clef"]:
            right += 1
        else:
            wrong += 1
            print(f"    FALSE POSITIVE  staff {i}: read {got}, truth {want['clef']}")
    print(f"  {right}/{n_c} C clefs located   false positives {wrong}")
    return right, wrong, n_c


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--reference", type=Path, default=HERE / "reference-clefs.pdf")
    ap.add_argument("--piano", type=Path, default=HERE / "piano-false-positives.pdf")
    ap.add_argument("--nottebohm", type=Path,
                    default=Path.home() / "Downloads"
                    / "Nottebohm-Beethovens-Studien-1873.pdf")
    ap.add_argument("--truth", type=Path, default=HERE / "nottebohm-p46-ground-truth.json")
    ap.add_argument("--orchestral", type=Path,
                    default=REPO / "tools/omr/training/data/imslp"
                    / "beethoven-symphony-5/pdfs/imslp-575951/score.pdf")
    ap.add_argument("--orchestral-spec", type=Path,
                    default=HERE / "beethoven5-clef-spot-check.json")
    # The corpus the F-clef veto had been missing: every staff the locator
    # LOCATES a C clef on across pages 2-80 with clustering on, read by eye.
    # Seventeen are bass clefs and seven are treble — the reads a veto change
    # is supposed to remove, and which appear in none of the other four.
    ap.add_argument("--sweep-spec", type=Path,
                    default=HERE / "beethoven5-clef-sweep.json")
    ap.add_argument("--reference-dpi", type=int, default=600)
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()

    missing = [p for p in (args.reference, args.piano) if not p.exists()]
    if missing:
        print("build the LilyPond corpora first:", file=sys.stderr)
        print("    cd benchmarks/omr-clef-geometry && lilypond "
              "reference-clefs.ly piano-false-positives.ly", file=sys.stderr)
        for p in missing:
            print(f"  missing {p}", file=sys.stderr)
        return 1

    exact, ref_wrong = check_reference(args.reference, args.reference_dpi)
    _staves, piano_wrong = check_piano(args.piano, (args.dpi, args.reference_dpi))
    if args.orchestral.exists():
        _f, orch_missed, orch_wrong = check_orchestral(
            args.orchestral, args.orchestral_spec, args.dpi)
        _sf, sweep_missed, sweep_wrong = check_orchestral(
            args.orchestral, args.sweep_spec, args.dpi,
            title="orchestral sweep — 24 staves that must be DECLINED")
    else:
        print(f"\norchestral spot check — skipped, no score at {args.orchestral}")
        orch_missed = orch_wrong = sweep_missed = sweep_wrong = 0
    if args.nottebohm.exists():
        right, cov_wrong, n_c = check_coverage(args.nottebohm, args.truth, args.dpi)
    else:
        print(f"\ncoverage — skipped, no PDF at {args.nottebohm}")
        right, cov_wrong, n_c = 0, 0, 0

    total_wrong = ref_wrong + piano_wrong + cov_wrong + orch_wrong + sweep_wrong
    print(f"\nreference {exact}/5 exact | coverage {right}/{n_c} | "
          f"orchestral misses {orch_missed} | sweep misses {sweep_missed} | "
          f"FALSE POSITIVES {total_wrong}")
    print("Report these separately. A missed clef costs nothing that was not "
          "already lost;\na wrong one transposes every note on its staff.")
    return 1 if (total_wrong or exact < 5) else 0


if __name__ == "__main__":
    raise SystemExit(main())
