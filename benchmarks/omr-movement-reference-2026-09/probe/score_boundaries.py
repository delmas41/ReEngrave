"""Score the lineup-boundary rule against HAND-READ movement openings.

The openings below were read off the print, not inferred: a movement opening
drops its first system down the page and names every staff in full, and each
page listed here was rendered and looked at (`out/tops/`). They are ground
truth for this probe and nothing else uses them.

The rule under test claims to find LINEUP boundaries, not movement boundaries,
so it is scored on both questions separately:

  * did it ever split where no movement begins?   (a FALSE boundary is the
    dangerous failure -- it mis-references a whole span)
  * of the movement openings it did NOT split at, is the lineup the same on
    both sides?  If it is, the split would have produced the same reference and
    missing it costs nothing; if it is not, the rule abstained to today's
    document-wide behaviour and is no worse than it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr import movement_reference as mr   # noqa: E402

#: page_index of every movement opening, hand-read from the print.
TRUTH = {
    "beet5-984073": [1, 17, 32, 44],
    "brahms1-317803": [0, 45],       # only p45 verified beyond the first
}


def peak_between(peak, lo, hi):
    vals = [v for p, v in peak.items() if lo <= p <= hi]
    return max(vals) if vals else None


def main(paths):
    for path in paths:
        d = json.load(open(path))
        key = Path(path).name.split(".")[0]
        rows = [(r["page"], r["systems"]) for r in d["rows"]]
        peak = mr._peaks(rows)
        spans = mr.lineup_spans(rows)
        found = [s[0] for s in spans][1:]          # the first is not a boundary
        truth = TRUTH.get(key)

        print(f"\n=== {key} ===")
        print(f"  boundaries found : {found}")
        if truth is None:
            print("  (no hand-read openings for this work; a rule that finds no "
                  "boundary can claim no opening falsely)")
            continue
        print(f"  movement openings: {truth}")
        false_pos = [b for b in found if b not in truth]
        print(f"  FALSE boundaries : {false_pos}  <- must be empty")
        missed = [t for t in truth[1:] if t not in found]
        for t in missed:
            lo = max([b for b in [truth[0]] + found if b < t] or [truth[0]])
            before = peak_between(peak, lo, t - 1)
            after = peak_between(peak, t, min(
                [x for x in truth + [10 ** 6] if x > t]) - 1)
            verdict = ("FREE -- same lineup level either side"
                       if before == after else
                       "abstained -- lineup grows, keeps today's reference")
            print(f"  missed opening p{t}: peak {before} -> {after}   {verdict}")


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(str(p) for p in Path(
        "benchmarks/omr-movement-reference-2026-09/out").glob(
            "*.staffprofile.json")))
