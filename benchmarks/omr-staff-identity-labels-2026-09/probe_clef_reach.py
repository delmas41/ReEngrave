#!/usr/bin/env python3
"""Could MORE label reach ever move the clef number? — the premise test.

The workstream was opened on a census finding: end-to-end clef accuracy is 90%
and **17 of the 21 errors are the positional default calling a bass or C-clef
staff treble**. The machinery meant to replace that default is
`clef_correction`, which takes a staff's instrument and proposes its
conventional clef — so the lever was assumed to be label REACH.

Phase 2 (ii-a) recovered 11 staves and applied **zero** clefs, because every
one of them is a horn or a trumpet, whose `default_clef` is `treble` — which
is what the positional default already guessed. That is one rule's result, and
it raises a question about the premise itself rather than about the rule:

    if the staves whose labels are recoverable are systematically in the
    families that DEFAULT CORRECTLY, then label reach cannot move the clef
    number however far it is pushed.

This asks it directly and cheaply. Over every staff in the 20-row corpus, take
the PRINTED TRUTH name (not the reading — the question is what the staff IS,
not what we managed to read), resolve it to an instrument, and cross-tabulate
its conventional clef against whether the label ladder resolved it.

    treble-family staves    the positional default is already right, so a
                            label there cannot fix a clef
    bass/alto/tenor staves  the default is wrong, so a label there is exactly
                            the lever the census described

⚠️ THIS IS ABOUT THE CEILING, NOT ABOUT ACCURACY. A bass-family staff whose
label is unresolved is an OPPORTUNITY for the clef lever, not a clef error —
the staff may be reading its clef correctly from the detector. The number this
prints is the largest the lever could possibly be, and the honest use of it is
to bound the premise, not to claim a gain.

════════════════════════════════════════════════════════════════════════════
MEASURED 2026-09-05, AND IT ANSWERS THE PREMISE: ON THIS CORPUS THE LABEL
LEVER CANNOT MOVE THE CLEF NUMBER AT ALL.

    staff family (by PRINTED truth)   resolved  unresolved   total
    alto-default                             8           7      15
    bass-default                            52          22      74
    treble-default                          95          33     128
    TOTAL                                  155          62     217

29 unresolved staves are in a family whose conventional clef is NOT treble —
the entire population `clef_correction` could ever be handed by more label
reach. Cross-tabulated against the Phase 1 classification:

    29 of 29  a_NO_LABEL_PRINTED

**Every one of them is behind the wall.** Not one is a lexicon refusal, a
group-label fragment or an OCR miss. They are Litolff Beethoven's Viola and
`Violoncello e Basso` on continuation systems, and Simrock Dvořák's whole
p6/p7 lineup — pages that print no margin label at all, proven by 0 ink in
the margin band (`probe_margin_ink.py`).

So the workstream's opening premise — "17 of 21 clef errors are the positional
default, and the machinery to replace it is starved of instrument names" — is
true about the machinery and FALSE about the remedy, at least here. The names
are not merely unread; on the staves that need them they are not printed. The
0 clefs applied by the shared-block rule is not that rule falling short: it is
the shape of the whole opportunity.

⚠️ WHAT THIS DOES NOT SAY. (1) It is 217 truth-carrying staves over 5
publishers, not the whole library — an edition that labels its strings on
every system would move it. (2) It says nothing about whether `clef_correction`
would get those staves RIGHT if it were handed them; it says it will not be
handed them. (3) The 60 already-resolved non-treble staves are a separate
question — whether their labels are actually reaching `clef_correction` is
about the consumer, not about reach, and is not measured here.
════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr.instruments import lookup                       # noqa: E402

TREBLE_DEFAULT = {"treble"}


def main() -> int:
    d = json.loads((HERE / "ladder.json").read_text())
    tab = defaultdict(Counter)
    unresolved_bass = []
    for r in d["rows"]:
        for s in r["staves"]:
            t = s.get("TRUTH_name")
            if not t:
                continue
            h = lookup(t)
            inst = h.instrument if (h and h.instrument) else None
            if inst is None:
                tab["UNKNOWN"]["resolved" if s.get("ladder_resolved")
                                else "unresolved"] += 1
                continue
            fam = "treble-default" if inst.default_clef in TREBLE_DEFAULT \
                else f"{inst.default_clef}-default"
            state = "resolved" if s.get("ladder_resolved") else "unresolved"
            tab[fam][state] += 1
            if state == "unresolved" and inst.default_clef not in TREBLE_DEFAULT:
                unresolved_bass.append((r["row_id"], s["system"],
                                        s["position"], t, inst.name,
                                        inst.default_clef))

    print(f"{'staff family (by PRINTED truth)':32} {'resolved':>9} "
          f"{'unresolved':>11} {'total':>7}")
    tot_r = tot_u = 0
    for fam in sorted(tab):
        c = tab[fam]
        tot_r += c["resolved"]
        tot_u += c["unresolved"]
        print(f"{fam:32} {c['resolved']:>9} {c['unresolved']:>11} "
              f"{sum(c.values()):>7}")
    print(f"{'TOTAL':32} {tot_r:>9} {tot_u:>11} {tot_r + tot_u:>7}")
    print()
    nb = len(unresolved_bass)
    print(f"UNRESOLVED staves whose instrument does NOT default to treble: {nb}")
    print("  — the whole population a further label gain could ever hand to "
          "`clef_correction`.")
    for row in unresolved_bass:
        print(f"    {row[0][:30]:30} s{row[1]} p{row[2]:>2}  {row[3]!r} "
              f"= {row[4]} ({row[5]})")
    (HERE / "clef-reach.json").write_text(json.dumps(
        {"table": {k: dict(v) for k, v in tab.items()},
         "unresolved_non_treble": unresolved_bass}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
