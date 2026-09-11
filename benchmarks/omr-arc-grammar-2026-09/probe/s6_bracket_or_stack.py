"""Two arcs around the same notes: a STACK, or a CHORD-TIE BRACKET?

⚠️⚠️ **THE CROPS SETTLED THIS AND NO AMOUNT OF COUNTING COULD.** On Litolff
Beethoven 5 the pairs a loose "stacked arcs" test finds are overwhelmingly a
DIFFERENT engraving: a two-note chord tied to the next chord gets **one tie
per note**, the upper drawn ABOVE the chord and the lower BELOW it, so the two
arcs BRACKET the noteheads. `crops/STACK01-p2s1st0-…` and
`crops/STACK04-p3s0st5-…` are that configuration unmistakably, and the record
classes both arcs `tie`, which is correct.

Sean's S6 is about two arcs on the SAME side of the notes: a tie hugging the
heads with a phrase slur drawn outside it. The two configurations are
identical to every test built from "x overlaps, y disjoint" — and OPPOSITE in
meaning, because S6 applied to a chord-tie bracket turns a correct tie into a
wrong slur.

So the discriminator is the NOTES, not the arcs:

    heads BETWEEN the two arcs     -> chord-tie bracket. S6 MUST NOT FIRE.
    both arcs on ONE side of them  -> Sean's stack. S6 could fire.

No constant: the test is strict between-ness on the heads the two arcs
already bind, and a pair where neither arc binds a head ABSTAINS rather than
being counted either way.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from typing import Any, Dict, List

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09/probe")
from s6_stacks import run as stacks_run  # noqa: E402


def classify(p: Dict[str, Any]) -> str:
    ys = list(p["lower_head_ys"]) + list(p["upper_head_ys"])
    if not ys:
        return "no_heads_bound"
    lo_mid = (p["lower_y0"] + p["lower_y1"]) / 2.0
    up_mid = (p["upper_y0"] + p["upper_y1"]) / 2.0
    # `upper` is the smaller y (higher on the page); `lower` the larger.
    between = [y for y in ys if up_mid < y < lo_mid]
    if len(between) == len(ys):
        return "bracket"          # every head sits inside the two arcs
    if not between:
        return "stack"            # every head is outside both
    return "mixed"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--max-gap", type=float, default=1.0)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = stacks_run(a.record)
    close = [p for p in r["pairs"] if (p["gap_spaces"] or 99) <= a.max_gap]
    kinds = collections.Counter(classify(p) for p in close)
    print(f"candidate pairs within {a.max_gap} staff space: {len(close)}")
    for k, v in kinds.most_common():
        print(f"    {k:16s} {v}")
    acting = [p for p in close
              if classify(p) == "stack"
              and p["lower_binds"] >= 2 and p["upper_binds"] >= 2]
    print(f"\npairs S6 could ACT on (a stack, both arcs binding 2+): "
          f"{len(acting)}")
    for p in acting:
        print(f"    {p['where']:14s} gap {p['gap_spaces']:.2f}  "
              f"lower={p['lower_kind']}/{p['lower_binds']} "
              f"upper={p['upper_kind']}/{p['upper_binds']}")
    brackets = [p for p in close if classify(p) == "bracket"]
    wrong = [p for p in brackets
             if p["lower_kind"] == "tie" and p["upper_kind"] == "tie"]
    print(f"\nchord-tie BRACKETS a naive S6 would damage "
          f"(both arcs read tie): {len(wrong)}")
    if a.out:
        json.dump({"close": close,
                   "classified": {k: v for k, v in kinds.items()}},
                  open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
