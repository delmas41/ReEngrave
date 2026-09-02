"""Count the measures on a scanned page WITHOUT asking the pipeline.

Generalised from `benchmarks/omr-first-run-2026-08/probe_page_measures.py`,
which was hard-coded to one PDF, one page and five hand-entered staff bands.
The rules and their constants are carried over unchanged — they were paid for.

    # 1. find the staff bands and eyeball them on the overlay
    python3 benchmarks/omr-scan-e2e-2026-09/probe_page_measures.py \
        --pdf /abs/score.pdf --page 1 --bands-only --overlay /tmp/bands.png

    # 2. count on the bands that are TACET for the whole page
    python3 benchmarks/omr-scan-e2e-2026-09/probe_page_measures.py \
        --pdf /abs/score.pdf --page 1 --staves 0 1 5 6 7

THE TRICK IS THE CHOICE OF STAFF. On a staff carrying notes, stems and beams
are full-height ink too, so a column test finds far more than barlines. On a
staff of whole-bar RESTS almost the only full-height ink is a barline — a whole
rest is a short thick horizontal hanging off the fourth line and never spans the
staff. The count is exact on a tacet staff and unreliable everywhere else, so
the caller names the tacet staves and this refuses to guess.

⚠️ A TIME SIGNATURE IS FULL-HEIGHT INK TOO — numerator across the upper two
spaces, denominator across the lower two. Counting it made Beethoven 5 page 1
seventeen measures when it is sixteen, and five staves agreed on the wrong
answer because all five print the same meter. **Agreement across staves cannot
catch an error every staff shares.** What separates them is that a barline
continues past the staff into the gap and a meter stops at the staff lines:
measured on that page, every real barline scores 1.00 reach and the time
signature 0.05.

⚠️ A cross-staff variant (a column dark in >= 8 of 12 staves) was tried in the
original and is NOT used: it returns 12 on that page, because where the strings
play thickly the barline meets noteheads and stops being a clean column. It
fails in the same place the pipeline fails, which is the one thing an
independent check may not do.

STAFF BANDS ARE FOUND HERE, NOT TAKEN FROM THE PIPELINE. The original read them
out of `staff_geometry` in the run it was checking. This finds five-line groups
by horizontal projection and draws them, so a human confirms the geometry before
any count is believed — the same division of labour, with the pipeline out of it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import fitz
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover - host dependency
    raise SystemExit(f"needs pymupdf + pillow: {exc}")

#: A column counts as full-height ink at this dark fraction. Loose enough for a
#: barline broken by the scan, tight enough that a whole rest cannot reach it.
DARK_FRACTION = 0.92

#: The furniture at a system's left edge — the initial rule, the bracket, and a
#: subgroup's curly brace — is full-height ink that reaches past the staff, so
#: every rule here passes it. Collapse the whole leading CLUSTER, not just a
#: pair: on Dvorak 9 the Violino I/II staves carry a brace 2.4 staff spaces
#: right of the rule and the trombone and timpani staves do not, which showed up
#: as those two staves reporting 9 measures against the others' 8 while every
#: INTERIOR barline agreed to within 6 px across all four. The constant is set
#: past that brace and nowhere near real music: the narrowest interior measure
#: on any page measured here is 18 staff spaces wide.
BRACKET_MERGE_SPACES = 3.0

#: How far beyond the staff to look for the column continuing, and how much of
#: that strip must be inked. A barline is drawn THROUGH the gap to the next
#: staff of its bracketed group; a time signature stops at the staff lines.
#: EITHER side counts, because a barline stops at a group boundary — the bottom
#: staff of a bracket has nothing below it.
REACH_SPACES = 1.4
REACH_MIN_INK = 0.5

#: A barline is about a fifth of a staff space wide; a digit is more than a
#: whole one. Width alone cannot separate them (a 2/4's digits align into a
#: column six pixels wide, exactly a barline's width) but it is a cheap first cut.
MAX_BARLINE_WIDTH_SPACES = 0.55


def render(pdf: Path, page: int, dpi: int) -> np.ndarray:
    with fitz.open(pdf) as doc:
        if page >= doc.page_count:
            raise SystemExit(f"{pdf.name} has {doc.page_count} pages; no index {page}")
        pix = doc[page].get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
    return np.array(img)


def find_bands(page: np.ndarray, *, min_cover: float = 0.45) -> list[tuple[int, int]]:
    """Five-line staff groups, by horizontal projection over the page's middle.

    A staff line is a row inked across most of the width. Rows are grouped into
    runs (a line is 1-3 px thick), and five consecutive runs whose spacing is
    consistent make a staff. Nothing here knows what a staff is FOR; it is a
    geometry finder whose output a human confirms on the overlay.
    """
    h, w = page.shape
    mid = page[:, int(w * 0.20):int(w * 0.80)] < 128
    cover = mid.mean(axis=1)
    rows = np.where(cover > min_cover)[0]
    if rows.size == 0:
        return []
    runs: list[list[int]] = []
    for y in rows:
        if runs and y - runs[-1][-1] <= 2:
            runs[-1].append(int(y))
        else:
            runs.append([int(y)])
    centres = [int(np.mean(r)) for r in runs]

    bands: list[tuple[int, int]] = []
    i = 0
    while i + 4 < len(centres):
        window = centres[i:i + 5]
        gaps = np.diff(window)
        # A staff's four gaps are equal to within scan noise.
        if gaps.min() > 2 and gaps.max() <= gaps.min() * 1.6:
            bands.append((window[0], window[4]))
            i += 5
        else:
            i += 1
    return bands


def columns(page: np.ndarray, y0: int, y1: int) -> tuple[list[int], list[dict]]:
    """Full-height columns in a staff band that also continue past it."""
    spacing = max((y1 - y0) / 4.0, 1.0)
    dark = (page[y0:y1 + 1, :] < 128).mean(axis=0) > DARK_FRACTION
    runs: list[list[int]] = []
    for x in np.where(dark)[0]:
        if runs and x - runs[-1][-1] <= 4:
            runs[-1].append(int(x))
        else:
            runs.append([int(x)])

    reach_px = max(int(REACH_SPACES * spacing), 4)
    above = page[max(0, y0 - 3 - reach_px):max(0, y0 - 3), :] < 128
    below = page[y1 + 3:y1 + 3 + reach_px, :] < 128

    kept, rejected = [], []
    for run in runs:
        width_spaces = (run[-1] - run[0] + 1) / spacing
        reach = 0.0
        for strip in (above[:, run[0]:run[-1] + 1], below[:, run[0]:run[-1] + 1]):
            if strip.size:
                reach = max(reach, float(strip.mean(axis=0).max()))
        info = {"x": int(np.mean(run)), "width_spaces": round(width_spaces, 2),
                "reach": round(reach, 2)}
        if width_spaces > MAX_BARLINE_WIDTH_SPACES:
            info["why"] = "too wide"
        elif reach < REACH_MIN_INK:
            info["why"] = "stops at the staff"
        else:
            kept.append(int(np.mean(run)))
            continue
        rejected.append(info)

    merge_px = BRACKET_MERGE_SPACES * spacing
    while len(kept) > 1 and kept[1] - kept[0] < merge_px:
        kept = kept[1:]
    return kept, rejected


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--page", type=int, required=True, help="0-based page index")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--staves", type=int, nargs="+", default=None,
                    help="indices into the detected bands — name only staves "
                         "that are TACET for the whole page")
    ap.add_argument("--bands-only", action="store_true",
                    help="list the detected bands and exit")
    ap.add_argument("--overlay", type=Path, default=None,
                    help="write a PNG with the bands drawn, for eyeballing")
    ap.add_argument("--show-rejected", action="store_true",
                    help="print the columns that were thrown out and why")
    ap.add_argument("--min-cover", type=float, default=0.45)
    args = ap.parse_args(argv)

    page = render(args.pdf, args.page, args.dpi)
    bands = find_bands(page, min_cover=args.min_cover)
    print(f"{args.pdf.name} page index {args.page} at {args.dpi} dpi "
          f"({page.shape[1]}x{page.shape[0]}): {len(bands)} five-line bands")
    for i, (y0, y1) in enumerate(bands):
        print(f"   band {i:2d}  y {y0:5d}-{y1:5d}  height {y1 - y0:4d} "
              f"(space {(y1 - y0) / 4:.1f})")

    if args.overlay:
        rgb = Image.fromarray(page).convert("RGB")
        draw = ImageDraw.Draw(rgb)
        for i, (y0, y1) in enumerate(bands):
            draw.rectangle([2, y0 - 2, rgb.width - 3, y1 + 2],
                           outline=(220, 0, 0), width=3)
            draw.text((8, max(0, y0 - 26)), str(i), fill=(220, 0, 0))
        scale = 1400 / rgb.width
        rgb.resize((1400, int(rgb.height * scale))).save(args.overlay)
        print(f"   wrote {args.overlay}")

    if args.bands_only or not args.staves:
        if not args.bands_only:
            print("\nno --staves given; nothing counted "
                  "(name only TACET staves — see the module docstring)")
        return 0

    counts = []
    for idx in args.staves:
        if idx >= len(bands):
            print(f"!! band {idx} does not exist", file=sys.stderr)
            return 1
        y0, y1 = bands[idx]
        bars, rejected = columns(page, y0, y1)
        counts.append(len(bars) - 1)
        print(f"\nband {idx:2d} (y {y0}-{y1}): barlines={len(bars):3d}  "
              f"measures={len(bars) - 1:3d}")
        print(f"   x: {bars}")
        if args.show_rejected and rejected:
            for r in rejected:
                print(f"   rejected x={r['x']:5d} w={r['width_spaces']:4.2f}sp "
                      f"reach={r['reach']:4.2f}  {r['why']}")

    agreed = set(counts)
    print()
    if len(agreed) == 1:
        print(f"all {len(counts)} named staves agree: {counts[0]} measures")
        print("⚠️  agreement is NOT proof — every staff prints the same time "
              "signature,\n    and that is how this probe once returned 17 on a "
              "16-measure page. Pair it\n    with evidence that fails "
              "differently (a meter change in the reference,\n    a rehearsal "
              "number, a printed bar number).")
    else:
        print(f"staves DISAGREE {sorted(agreed)} — do not use as ground truth")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
