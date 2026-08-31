"""Count the measures on a scanned page WITHOUT asking the pipeline.

Scoring a page against a reference needs to know which measures the page holds,
and taking that number from the thing under test is worthless. This counts them
from the ink.

THE TRICK IS THE CHOICE OF STAFF. On a staff carrying notes, stems and beams are
full-height ink too, so a column test finds far more than barlines. On a staff of
whole-bar RESTS almost the only full-height ink is a barline — a whole rest is a
short thick horizontal hanging off the fourth line and never spans the staff. So
the count is exact on a tacet staff and unreliable everywhere else.

⚠️ ALMOST. **A time signature is full-height ink too** — numerator across the
upper two spaces, denominator across the lower two — and the first version of
this counted it as a barline, making Beethoven 5 page 1 seventeen measures when
it is sixteen. Five staves agreed on the wrong answer, because all five print
the same time signature: agreement across staves cannot catch an error every
staff shares. It is separated by WIDTH — a barline is about a fifth of a staff
space wide and a digit more than a whole one — which is what
`MAX_BARLINE_WIDTH_SPACES` is for.

Beethoven 5 page 1 has five tacet staves — Flauti, Oboi, Corni, Trombe, Timpani
— and all five return 16.

    python3 benchmarks/omr-first-run-2026-08/probe_page_measures.py

A cross-staff variant (a column dark in >= 8 of the 12 staves) was tried and is
NOT used: it returns 12, because where the strings play thickly the barline meets
notes and stops being a clean full-height column. It fails in the same place the
pipeline fails, which is exactly what an independent check must not do.
"""
from __future__ import annotations

import numpy as np

try:
    import fitz
    from PIL import Image
except ImportError as exc:  # pragma: no cover - host dependency
    raise SystemExit(f"needs pymupdf + pillow: {exc}")

PDF = ("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus/"
       "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf")
PAGE = 1
DPI = 600

#: (name, first staff line y, last staff line y) at 600 dpi, from the run's own
#: `staff_geometry`. Only staves that are tacet for the whole page qualify — see
#: the module docstring.
TACET_STAVES = [
    ("Flauti", 1148, 1210),
    ("Oboi", 1310, 1373),
    ("Corni", 1836, 1898),
    ("Trombe", 1994, 2057),
    ("Timpani", 2154, 2216),
]

#: A column counts as full-height ink at this dark fraction. Loose enough for a
#: barline broken by the scan, tight enough that a whole rest cannot reach it.
DARK_FRACTION = 0.92

#: The system's opening bracket and initial rule sit within a few px of each
#: other; collapse the pair so the first measure is not counted twice.
BRACKET_MERGE_PX = 25

#: How far beyond the staff to look for the column continuing, and how much of
#: that strip must be inked. A barline is drawn THROUGH the gap to the next
#: staff of its bracketed group; a time signature stops at the staff lines.
#: EITHER side counts, because a barline stops at a group boundary: Timpani is
#: the bottom staff of its bracket here, so looking only below it found one
#: barline out of seventeen. Measured on this page:
#: every real barline scores 1.00 and the time signature 0.05, so the threshold
#: is not doing delicate work.
#:
#: Width cannot make this distinction and was tried first: the 2/4's digits
#: align into a column six pixels wide, exactly a barline's width.
BELOW_STAFF_PX = 22
BELOW_STAFF_MIN_INK = 0.5


def columns(page: np.ndarray, y0: int, y1: int) -> list[int]:
    dark = (page[y0:y1 + 1, :] < 128).mean(axis=0) > DARK_FRACTION
    runs: list[list[int]] = []
    for x in np.where(dark)[0]:
        if runs and x - runs[-1][-1] <= 4:
            runs[-1].append(x)
        else:
            runs.append([x])
    # Keep only the columns that carry on past the staff — see BELOW_STAFF_PX.
    above = page[max(0, y0 - 3 - BELOW_STAFF_PX):max(0, y0 - 3), :] < 128
    below = page[y1 + 3:y1 + 3 + BELOW_STAFF_PX, :] < 128
    kept = []
    for run in runs:
        reach = 0.0
        for strip in (above[:, run[0]:run[-1] + 1], below[:, run[0]:run[-1] + 1]):
            if strip.size:
                reach = max(reach, float(strip.mean(axis=0).max()))
        if reach >= BELOW_STAFF_MIN_INK:
            kept.append(run)
    centres = [int(np.mean(r)) for r in kept]
    if len(centres) > 1 and centres[1] - centres[0] < BRACKET_MERGE_PX:
        centres = centres[1:]
    return centres


def main() -> None:
    doc = fitz.open(PDF)
    pix = doc[PAGE].get_pixmap(dpi=DPI)
    page = np.array(
        Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    )
    counts = []
    for name, y0, y1 in TACET_STAVES:
        bars = columns(page, y0, y1)
        counts.append(len(bars) - 1)
        print(f"{name:9s} barlines={len(bars):3d}  measures={len(bars) - 1:3d}")
    agreed = set(counts)
    verdict = counts[0] if len(agreed) == 1 else None
    print()
    if verdict is None:
        print(f"staves DISAGREE {sorted(agreed)} — do not use as ground truth")
    else:
        print(f"all {len(counts)} tacet staves agree: {verdict} measures on page "
              f"{PAGE}")


if __name__ == "__main__":
    main()
