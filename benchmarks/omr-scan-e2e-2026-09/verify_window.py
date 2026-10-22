"""Check a measure window against the reference's CONTENT, not against ink.

The probe next door counts barlines. It is good, and it is not enough: it once
returned seventeen on a sixteen-measure page and five staves agreed, because a
time signature is full-height ink too and all five print the same one.
Agreement across staves cannot catch an error every staff shares, so a window
needs a second witness whose failure mode is different.

This is that witness. It prints, from the trimmed reference, a grid of which
parts SOUND in which measure of the window — and, either side of it, what the
neighbouring measures do. A reader compares the grid to the printed page:

    an entry the grid predicts and the page does not show, or a rest the grid
    predicts where the page has notes, means the window is misaligned.

It fails on encoding differences and on transposition; it cannot fail on a
column of ink being mistaken for a barline. That is the point — the two checks
are wrong about different things, so agreeing is worth something.

    .venv-omrned/bin/python benchmarks/omr-scan-e2e-2026-09/verify_window.py \
        --source /abs/reference.mxl --first 0 --last 8 --context 2

Runs inside `.venv-omrned` for the same reason `trim_reference.py` does, and
like it must not import `tools.*`.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from music21 import converter


def grid(source: Path, first: int, last: int, context: int) -> None:
    score = converter.parse(str(source))
    parts = list(score.parts)
    lo, hi = first - context, last + context

    numbers: list[int] = []
    activity: dict[int, dict[int, int]] = {}
    for pi, part in enumerate(parts):
        row: dict[int, int] = {}
        for measure in part.getElementsByClass("Measure"):
            n = measure.number
            if n is None or not (lo <= n <= hi):
                continue
            row[n] = len(list(measure.recurse().notes))
            if n not in numbers:
                numbers.append(n)
        activity[pi] = row
    numbers.sort()

    name_w = max((len(p.partName or f"part {i}") for i, p in enumerate(parts)),
                 default=10)
    name_w = min(name_w, 28)

    header = " " * (name_w + 2)
    for n in numbers:
        header += f"{n:>4d}"
    print(header)
    marker = " " * (name_w + 2)
    for n in numbers:
        marker += "  ##" if first <= n <= last else "   ."
    print(marker + "     (## = in the window)")

    for pi, part in enumerate(parts):
        name = (part.partName or f"part {pi}")[:name_w]
        line = f"{name:<{name_w}}  "
        for n in numbers:
            count = activity[pi].get(n)
            line += "   -" if count is None else ("   ." if count == 0
                                                  else f"{count:>4d}")
        print(line)

    print()
    print("  '.' = measure present but silent (rests), a number = sounding "
          "note objects,\n  '-' = the part has no such measure.")
    sounding = [n for n in numbers
                if any(activity[pi].get(n, 0) for pi in range(len(parts)))]
    print(f"  measures with any sound in {lo}..{hi}: {sounding}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--first", type=int, required=True)
    ap.add_argument("--last", type=int, required=True)
    ap.add_argument("--context", type=int, default=2,
                    help="measures to show either side of the window — the "
                         "point is what the page should NOT contain")
    args = ap.parse_args(argv)
    grid(args.source, args.first, args.last, args.context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
