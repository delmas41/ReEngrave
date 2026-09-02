"""Every wrong duration in a pair, as the ratio predicted/true.

The house diagnostic from `WRONG_NOTE_ATTRIBUTION_2026-09-01.md`: a duration
fault is named by its RATIO, not by its size. x0.5 is a beam level too many,
x2 one too few, x1.5 a triplet read straight, x0.667 a dot lost. A ratio that
is none of those is a different mechanism and worth opening.

Aligned BY MEASURE AND INDEX, for the reason `attribute_wrong_notes` gives:
aligning on pitch names cannot see a uniformly wrong part at all.

    python3 benchmarks/omr-corpus-widening-2026-09/probe_duration_ratios.py \
        --works mozart-sym41-mvt1 --fixtures <dir>

Host Python; needs music21, not musicdiff.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from music21 import converter

ROOT = Path(__file__).resolve().parents[2]


def seq(path: Path):
    """part index -> measure number -> [(pitch tuple, quarterLength)]."""
    score = converter.parse(str(path))
    out: dict[int, dict] = {}
    names: dict[int, str] = {}
    for i, part in enumerate(score.parts):
        names[i] = (part.partName or f"part{i}").strip()
        bars: dict = {}
        for m in part.getElementsByClass("Measure"):
            evs = []
            for n in m.recurse().notes:
                ps = tuple(sorted(p.midi for p in n.pitches))
                evs.append((ps, Fraction(n.duration.quarterLength).limit_denominator(64)))
            bars[m.number] = evs
        out[i] = bars
    return out, names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", nargs="+", required=True)
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--detail", action="store_true")
    args = ap.parse_args()

    for work in args.works:
        pred, pnames = seq(args.fixtures / f"{work}.omr.musicxml")
        truth, tnames = seq(args.fixtures / f"{work}.musicxml")
        ratios: Counter = Counter()
        per_part: dict[int, Counter] = defaultdict(Counter)
        truth_dur: Counter = Counter()
        wrong_by_truth_dur: Counter = Counter()
        n_paired = n_wrong = 0
        examples: dict[Fraction, list] = defaultdict(list)
        for pi in sorted(set(pred) & set(truth)):
            for bar in sorted(set(pred[pi]) & set(truth[pi])):
                pe, te = pred[pi][bar], truth[pi][bar]
                if len(pe) != len(te):
                    continue
                for (pp, pd), (tp, td) in zip(pe, te):
                    n_paired += 1
                    truth_dur[td] += 1
                    if pd != td:
                        n_wrong += 1
                        r = Fraction(pd, td) if td else None
                        ratios[r] += 1
                        per_part[pi][r] += 1
                        wrong_by_truth_dur[td] += 1
                        if len(examples[r]) < 6:
                            examples[r].append(
                                f"{tnames.get(pi, pi)[:18]} m{bar} {td}->{pd}")
        print(f"\n=== {work}: {n_wrong} wrong of {n_paired} paired notes "
              f"({100.0 * n_wrong / max(1, n_paired):.1f}%)")
        print("  ratio pred/true   notes   what it usually is")
        NAME = {Fraction(1, 2): "beam level one too many",
                Fraction(2): "beam level one too few",
                Fraction(3, 2): "triplet read straight",
                Fraction(2, 3): "dotted note read undotted",
                Fraction(1, 4): "two beam levels too many",
                Fraction(4): "lost every beam it had",
                Fraction(3, 4): "?", Fraction(4, 3): "?"}
        for r, n in ratios.most_common():
            print(f"  {str(r):>14s}   {n:>5d}   {NAME.get(r, '')}")
            if args.detail:
                for e in examples[r]:
                    print(f"                          {e}")
        print("  by TRUE duration (wrong / total):")
        for d in sorted(truth_dur, key=lambda x: -truth_dur[x]):
            print(f"    {str(d):>8s} ql   {wrong_by_truth_dur[d]:>4d} / "
                  f"{truth_dur[d]:>4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
