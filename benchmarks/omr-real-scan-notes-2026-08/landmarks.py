"""Print the marks that let a human confirm a page's bar range by eye.

    python3 benchmarks/omr-real-scan-notes-2026-08/landmarks.py --page beet5-p2
    python3 benchmarks/omr-real-scan-notes-2026-08/landmarks.py --page beet5-p2 \
        --first 1 --last 40          # test a rival hypothesis

WHY THIS AND NOT A BARLINE COUNTER. The obvious tool here counts barlines from
the pixels. One was written and thrown away: on this print a column-of-ink test
returns 15, 16 or 17 bars for the same system depending on the ink threshold,
because note stems make full-height columns and faded barlines do not. It
agreed with the truth about as often as it disagreed, and a cross-check that is
wrong half the time is worse than none — it would have talked a later reader
out of a correct hand count.

What settled the range instead was landmarks: printed marks so distinctive that
their bar is unmistakable, whose bar NUMBER the MusicXML also gives. If the
score says a fermata falls in m.21 and a 'ff' in m.22, and the page shows a
fermata one bar before a 'ff' six bars after the system's first barline, then
that system starts at m.17 and there is no arithmetic to get wrong.

So this script does the mechanical half — pulling every such mark out of the
MusicXML for a proposed range and saying which bar it belongs to — and leaves
the half only eyes can do. It makes no claim about the page. Point it at a
range you are testing, look at the scan, and see whether the marks are where it
says. A wrong range will disagree loudly, because dynamics and fermatas are
sparse and their SPACING is a fingerprint.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pages import gradus_path, page_config  # noqa: E402


def measure_landmarks(m: Any) -> list[str]:
    """The marks on one measure that a reader could pick out at a glance."""
    from music21 import dynamics, expressions

    marks: list[str] = []
    for d in m.getElementsByClass(dynamics.Dynamic):
        marks.append(d.value)
    for d in m.getElementsByClass(dynamics.DynamicWedge):
        marks.append(type(d).__name__.lower())
    for element in m.notesAndRests:
        for ex in element.expressions:
            if isinstance(ex, expressions.Fermata):
                marks.append("fermata")
            elif isinstance(ex, expressions.Trill):
                marks.append("trill")
        for pitch in getattr(element, "pitches", ()):
            # An accidental printed against the key signature is as visible as
            # a dynamic, and far rarer than a notehead.
            if pitch.accidental is not None and pitch.accidental.displayStatus:
                marks.append(f"{pitch.nameWithOctave}!")
    return marks


def shape(m: Any) -> str:
    """A one-glance description of the bar's rhythm, for orientation."""
    bits = []
    for e in m.notesAndRests:
        ql = float(e.duration.quarterLength)
        bits.append(("r" if e.isRest else "n") + f"{ql:g}")
    return " ".join(bits) if bits else "(empty)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--page", default="beet5-p2")
    ap.add_argument("--part", action="append",
                    help="Gradus part name; repeatable. Default: the scored parts")
    ap.add_argument("--first", type=int, default=None)
    ap.add_argument("--last", type=int, default=None)
    ap.add_argument("--all-bars", action="store_true",
                    help="also print bars carrying no landmark")
    args = ap.parse_args(argv)

    from music21 import converter

    cfg = page_config(args.page)
    first = args.first if args.first is not None else cfg["first_measure"]
    last = args.last if args.last is not None else cfg["last_measure"]
    names = args.part or [p["gradus_part"] for p in cfg["parts"]]

    score = converter.parse(str(gradus_path(cfg["work_id"])))
    by_name = {p.partName: p for p in score.parts}

    # Where each system starts, so a reader knows which staff line to scan.
    starts, at = [], first
    for n in cfg["systems"]:
        starts.append((at, at + n - 1))
        at += n
    proposed = last - first + 1
    print(f"page {cfg['id']}: testing mm.{first}-{last} ({proposed} bars)")
    if proposed == sum(cfg["systems"]):
        for i, (lo, hi) in enumerate(starts):
            print(f"  system {i}: mm.{lo}-{hi} ({hi - lo + 1} bars)")
    else:
        print(f"  NOTE: {proposed} bars does not match the hand-read layout "
              f"{cfg['systems']} (= {sum(cfg['systems'])} bars), so the "
              f"per-system split below is not shown.")

    for name in names:
        part = by_name.get(name)
        if part is None:
            print(f"\n{name}: not in this score")
            continue
        print(f"\n--- {name} ---")
        n_marked = 0
        for m in part.getElementsByClass("Measure"):
            if m.number is None or not (first <= m.number <= last):
                continue
            marks = measure_landmarks(m)
            if marks:
                n_marked += 1
                print(f"  m{m.number:<4d} {', '.join(marks):28s} {shape(m)}")
            elif args.all_bars:
                print(f"  m{m.number:<4d} {'':28s} {shape(m)}")
        if not n_marked:
            print("  (no landmarks in range — check a different part)")

    print("\nNow look at the scan. If these marks fall in these bars, counting "
          "from the first barline of the system, the range is right.")
    print("If they are shifted by a constant, the range is off by that much; "
          "if they do not line up at all, it is the wrong page or the wrong "
          "edition, and NOTHING here should be scored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
