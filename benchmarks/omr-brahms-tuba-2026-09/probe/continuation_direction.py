"""Can the layout model say WHICH neighbour continues onto the extra staff?

`constrain` (removing `Tuba` from the layout because the work has none) gives
slot 9 to **Timpani**, not to Trombone — so removing the wrong candidate does
not produce the right answer. This asks whether that is a TIE the DP broke
arbitrarily or a preference the model actually holds, by scoring the two
readings as explicit layouts.

Also asks the prior question: with no labels at all, what does the layout
library make of a 16-staff Brahms finale?

Usage:  continuation_direction.py BLOB.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.score_layouts import (  # noqa: E402
    LAYOUTS, ScoreLayout, align_to_layout, fit_layouts)

TRUTH = ["Flute", "Oboe", "Clarinet", "Bassoon", "Contrabassoon", "Horn",
         "Horn", "Trumpet", "Trombone", "Trombone", "Timpani", "Violin",
         "Violin", "Viola", "Cello", "Contrabass"]


def main(path: str) -> None:
    b = (json.loads(Path(path).read_text())
         .get("contextual", {})["absent_instrument_veto"])
    si = {s["slot"]: s for s in b["slot_instruments"]}
    n = b["reference_size"]
    labels = {k: v["instrument"] for k, v in si.items()
              if v["source"] in ("label", "roster")}

    win = fit_layouts(n, labels=labels).layout
    no_tuba = tuple(p for p in win.parts if p != "Tuba")
    i = no_tuba.index("Trombone")
    j = no_tuba.index("Timpani")
    arms = {
        "as shipped (Tuba present)": win.parts,
        "Tuba removed": no_tuba,
        "Tuba removed, Trombone twice":
            no_tuba[:i + 1] + ("Trombone",) + no_tuba[i + 1:],
        "Tuba removed, Timpani twice":
            no_tuba[:j + 1] + ("Timpani",) + no_tuba[j + 1:],
    }
    print(f"{path}\n  Which reading of slot 9 does the DP actually prefer?\n")
    print("  arm                              total   /staff   slot9")
    for name, parts in arms.items():
        lay = ScoreLayout(name, parts)
        tot, assign = align_to_layout(lay, n, labels, None)
        print(f"  {name:<32s} {tot:7.2f} {tot / n:7.3f}   {assign[9]}")

    print("\n  With NO labels at all — what the layout library alone says:")
    blind = fit_layouts(n, labels=None, clefs=None)
    if blind is None:
        print("   fit_layouts -> None (abstains)")
    else:
        ok = sum(1 for a, t in zip(blind.assignment, TRUTH) if a == t)
        print(f"   layout={blind.layout.name}  {ok}/{n} match the hand-read "
              f"truth")
        for k, (a, t) in enumerate(zip(blind.assignment, TRUTH)):
            print(f"    {k:2d} fit={str(a):<15s} truth={t:<15s}"
                  f"{'' if a == t else '  X'}")


if __name__ == "__main__":
    main(sys.argv[1])
