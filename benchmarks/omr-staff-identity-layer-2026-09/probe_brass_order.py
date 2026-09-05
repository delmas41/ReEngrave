#!/usr/bin/env python3
"""Why does the brass appear to change order? — four hypotheses, checked.

MEASUREMENT ONLY. Reads hand-read page truth and the layout tables; opens no
new question about the detector.

Sean asked whether the brass reorders because a soloist or obbligato is
promoted above its section. The four candidate explanations want different
responses, and they are separated by CONSISTENCY -- a soloist is one part in
one work; a tradition is every staff of that family in that edition, on every
system and every page:

    1 promoted soloist / obbligato   ONE part behaving unusually in ONE work
    2 genuine placement convention   EVERY horn staff in an edition moving
                                     together, on every system and page
    3 our layouts encode ONE tradition -> not the page's fault, and fixable
                                     with a second brass ordering
    4 a label misread on those staves

Checked cheapest-and-most-reframing first: (4), then (3) -- which needs no page
at all -- then (2)/(1) against the printed lineups.

⚠️ THE PRINTED NAMES ARE THE EVIDENCE, not the canonical instrument the lexicon
resolves them to. Canonicalisation is what created the phenomenon in the first
place (see below), so this probe prints `TRUTH_printed` throughout.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_brass_order.py

── RESULT 2026-09-05: THE BRASS DOES NOT CHANGE ORDER. ───────────────────────
All four hypotheses are ruled out, and the question has no phenomenon.

(4) LABEL MISREAD — ruled out by PROVENANCE. Truth provenance is
    `works.json:staves` (164) and `alias->works.json:staves` (34): every brass
    name is HAND-READ from the print. No OCR or lexicon read produced it.

(3) OUR LAYOUTS ENCODE ONE TRADITION — ruled out, and it needed no page:

        Horn     vs Trombone   unanimous   Horn first  (3 layouts)
        Horn     vs Trumpet    unanimous   Horn first  (6)
        Horn     vs Tuba       unanimous   Horn first  (4)
        Trombone vs Trumpet    unanimous   Trumpet first (3)
        Trombone vs Tuba       unanimous   Trombone first (3)
        Trumpet  vs Tuba       unanimous   Trumpet first (4)

    0 of 6 brass-internal pairs contested. There is no second tradition in our
    templates for a "second brass ordering" to encode.

(2) GENUINE PLACEMENT CONVENTION — ruled out BY THE PAGES. Every work prints
    the same relative order, Horn -> Trumpet -> Trombone, on every system:

        beethoven (Litolff, 3 sys)   Corni in Es | Trombe in C
        brahms    (Breitkopf, 5 sys) 4 Hörner in C 1./2. | 4 Hörner in Es 3./4.
                                     | 2 Trompeten in C
        dvorak    (Simrock, 4 sys)   Corni I.II. in E | Corni III.IV. in C
                                     | Trombe in E | Tromboni I.II.
                                     | Trombone basso

(1) PROMOTED SOLOIST / OBBLIGATO — no evidence. Nothing is out of order on any
    page, so there is no promotion to explain. (And as noted when the
    hypothesis was framed, a true concerto soloist is promoted ABOVE THE FIRST
    VIOLINS, out of the brass block entirely — not reordered within it.)

(0) MULTIPLICITY — what the evidence actually supports. 26 brass staves sit in
    a duplicated-instrument position. A work prints ONE instrument on TWO
    staves; both canonicalise to one lexicon name; our layouts hold one part
    for it; a plain LCS matches one occurrence and reports the other as "out of
    order".

⚠️ SO THE BRASS EXEMPTION IS NOT REPHRASED, IT IS WITHDRAWN. It does not become
"brass has two orderings and the page must say which" — the pages are perfectly
consistent and so are the layouts. There is no ordering problem here at all.
What there is, is a MULTIPLICITY problem, and it is a different thing needing a
different fix.

⚠️ AND THE SPLITS ARE PRINCIPLED, WHICH IS THE PART OF SEAN'S INSTINCT THAT
SURVIVES. A section is split across staves for a determinate reason, visible in
the printed names: Brahms splits four horns BY KEY (`in C` 1./2. against `in Es`
3./4. — they cannot share a staff because they transpose differently), and
Dvorak splits trombones BY REGISTER (`Tromboni I.II.` against `Trombone
basso`). So a page's own labels carry why the split happened. That is
page-derived and relational, and it is the mirror image of the condensed-parts
problem (`OMR_CONDENSED_PARTS`): there several PARTS share one staff, here one
INSTRUMENT spans several staves.

⚠️ It also connects to signal B: adjacent staves of the SAME instrument in
DIFFERENT KEYS (Horn in C beside Horn in Es) are exactly the case a
key-signature COMPARISON can see and an absolute reading cannot.

⚠️ n = 9 conflicts over 3 engravings, two of which are one plate. This is a
mechanism with evidence, not a general result about orchestral engraving.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from tools.omr import instruments as INST      # noqa: E402
from tools.omr.score_layouts import LAYOUTS    # noqa: E402

IDENT = HERE / "heldout-identity.json"
BRASS = {"Horn", "Trumpet", "Trombone", "Tuba", "Cornet"}


def main():
    recs = [r for r in json.loads(IDENT.read_text())["records"] if r["TRUTH"]]
    print(f"records with truth: {len(recs)}")

    # ── (4) a label misread? ────────────────────────────────────────────────
    print(f"\n{'='*70}\n(4) LABEL MISREAD — ruled out by PROVENANCE, not by "
          f"inspection\n{'='*70}")
    provs = Counter(r["truth_provenance"] for r in recs)
    print(f"  truth provenance: {dict(provs)}")
    print("  The brass truth is HAND-READ from the print into works.json"
          " `staves[]`.\n  No OCR or lexicon read produced it, so a label"
          " misread cannot be the cause.\n  ⚠️ A CANONICALISATION artifact"
          " still could be, and that is (0) below.")

    # ── (3) do OUR layouts disagree with each other about brass? ────────────
    print(f"\n{'='*70}\n(3) DO OUR LAYOUTS ENCODE ONE TRADITION? — needs no "
          f"page\n{'='*70}")
    pairs = defaultdict(Counter)
    for layout in LAYOUTS:
        parts = list(layout.parts)
        idx = {p: i for i, p in enumerate(parts)}
        for a, b in combinations(sorted(BRASS & set(parts)), 2):
            pairs[(a, b)]["a_first" if idx[a] < idx[b] else "b_first"] += 1
    n_contested = 0
    for (a, b), t in sorted(pairs.items()):
        mark = "CONTESTED" if len(t) > 1 else "unanimous"
        if len(t) > 1:
            n_contested += 1
        print(f"   {a:9s} vs {b:9s}  {mark:9s}  {dict(t)}")
    print(f"\n  brass-internal pairs contested among our layouts: "
          f"{n_contested} of {len(pairs)}")
    if not n_contested:
        print("  ⇒ (3) RULED OUT. Every layout we hold agrees on brass order,"
              " so the\n    templates do not encode competing traditions and"
              " a 'second brass\n    ordering' would have nothing to encode.")

    # ── (2)/(1) what do the PAGES actually print? ───────────────────────────
    print(f"\n{'='*70}\n(2)/(1) WHAT THE PAGES PRINT — the brass block, in "
          f"order\n{'='*70}")
    by_sys = defaultdict(list)
    for r in recs:
        by_sys[(r["row_id"], r["system_index"])].append(r)
    seen_lineups = {}
    for key, group in sorted(by_sys.items()):
        group.sort(key=lambda r: r["ordinal"])
        brass = [(r["ordinal"], r["TRUTH_printed"], r["TRUTH"])
                 for r in group if r["TRUTH"] in BRASS]
        sig = tuple(b[1] for b in brass)
        seen_lineups.setdefault((key[0].rsplit("-p", 1)[0], sig), []).append(key)
    for (work, sig), keys in sorted(seen_lineups.items()):
        print(f"\n  {work}   ({len(keys)} systems)")
        for name in sig:
            print(f"      {name}")

    # ── (0) the explanation that actually fits ──────────────────────────────
    print(f"\n{'='*70}\n(0) MULTIPLICITY — the reading the evidence supports"
          f"\n{'='*70}")
    dup = 0
    for key, group in by_sys.items():
        group.sort(key=lambda r: r["ordinal"])
        c = Counter(r["TRUTH"] for r in group)
        dup += sum(v for k, v in c.items() if v > 1 and k in BRASS)
    print(f"  brass staves in a DUPLICATED-instrument position: {dup}")
    print("""
  Every 'conflict' is a work printing ONE instrument on TWO staves --
  `Horn I.II in C` beside `Horn III.IV in Es`, `Tromboni I.II.` beside
  `Trombone basso`. Both members of each pair canonicalise to a single lexicon
  name, our layouts hold ONE part for it, and a plain LCS can match only one
  occurrence. The second was reported as 'out of order'.

  ⚠️ NOTHING IS OUT OF ORDER ON ANY PAGE. The brass block reads in the same
  order in every system of every work here; what differs is HOW MANY STAVES it
  occupies. So Sean's question has no phenomenon to explain, and the answer to
  'why does the brass change order' is that it does not -- my probe's
  order-blind duplicate handling did.""")


if __name__ == "__main__":
    main()
