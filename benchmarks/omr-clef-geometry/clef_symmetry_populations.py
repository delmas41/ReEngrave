"""Does a symmetry floor separate the real C clefs from the misreads?

`min_symmetry_mezzosoprano` works because two populations that carry the same
label sit far apart in symmetry: the one real mezzosoprano scores 0.981 and
every misread scores under 0.82. The obvious next move is the same shape for
tenor, and this is the measurement that says whether it is available.

    python3 benchmarks/omr-clef-geometry/clef_symmetry_populations.py

For each sweep corpus it re-runs the locator, joins its reads to the hand-read
truth, and prints — per ANSWER — the symmetry of the reads that are real C
clefs against the reads that are not, plus the gap between them if there is
one. A floor is only available where the two ranges do not overlap.

Run it on every corpus, never one. The Beethoven-only answer for tenor is a
clean 0.014-wide gap; adding a second edition closes it completely, which is
the whole reason `mahler5-clef-sweep.json` was built.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
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

DEFAULT_SPECS = ("beethoven5-clef-sweep.json", "mahler5-clef-sweep.json")


def resolve_pdf(spec: dict) -> Path:
    raw = spec["pdf"]
    path = Path(raw).expanduser()
    return path if path.is_absolute() else (REPO / path)


def read_page(pdf: Path, page_index: int, dpi: int) -> dict[int, tuple[str, float]]:
    """The locator's read and its symmetry for every staff on one page.

    The same four preparation steps `check_clef_precision.read_page` takes, so
    the reads join to that harness's rows one for one.
    """
    page = render_page(pdf, page_index, dpi=dpi)
    pws = detect_barlines(detect_staves(page))
    remove_staff_lines(resegment_fused_measures(pws, extract_measures(pws)))
    out: dict[int, tuple[str, float]] = {}
    for staff_index, cell in header_cells_for_page(pws).items():
        found = locate_clef(cell)
        if found is not None:
            out[staff_index] = (found.read.name, found.symmetry)
    return out


def report(spec_path: Path, dpi: int) -> None:
    spec = json.loads(spec_path.read_text())
    pdf = resolve_pdf(spec)
    print(f"\n{spec_path.name} — {spec['source']}")
    if not pdf.exists():
        print(f"  skipped, no score at {pdf}")
        return

    by_page: dict[int, list[dict]] = defaultdict(list)
    for row in spec["staves"]:
        by_page[row["page"]].append(row)

    # answer -> "real" / "misread" -> [symmetry]
    pops: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"real": [], "misread": []})
    for page_index in sorted(by_page):
        read = read_page(pdf, page_index, dpi)
        for row in by_page[page_index]:
            got = read.get(row["staff"])
            if got is None:
                continue  # declined now; it is a miss, not a population member
            answer, symmetry = got
            pops[answer]["real" if row["c_clef"] else "misread"].append(symmetry)

    for answer in sorted(pops):
        real, bad = sorted(pops[answer]["real"]), sorted(pops[answer]["misread"])
        line = f"  {answer:<13}"
        line += (f" real {len(real):>3} [{real[0]:.3f} - {real[-1]:.3f}]"
                 if real else f" real {0:>3} {'':17}")
        line += (f"   misread {len(bad):>3} [{bad[0]:.3f} - {bad[-1]:.3f}]"
                 if bad else f"   misread {0:>3}")
        if real and bad:
            gap = real[0] - bad[-1]
            line += (f"   GAP {gap:+.3f}" if gap > 0
                     else f"   OVERLAP {-gap:.3f}")
        print(line)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--spec", type=Path, action="append",
                    help="sweep corpus JSON; repeatable. Default: every one.")
    ap.add_argument("--dpi", type=int, default=300)
    args = ap.parse_args()
    specs = args.spec or [HERE / name for name in DEFAULT_SPECS]
    for spec in specs:
        report(spec, args.dpi)
    print("\nA floor is available only where a GAP is printed, and only where "
          "it is\nprinted on EVERY edition. One edition's gap is one printer's "
          "ink.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
