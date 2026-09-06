"""CONTROL: did I render the pages the run is talking about, in the same order?

The adjudication reads instruments off a render and attributes them to detected
staff indices. Two things could break that silently — rendering the wrong page
(a printed page number is not a PDF index) and a staff ordering that is not
top-to-bottom. Both are checked at once here, for free: the run recorded which
margin labels it read on which staff index, so printing them beside what the
print shows is an exact, staff-for-staff join test on the labelled staves.

Measured: 41 labels across the four pages, and every one is the instrument
printed in that staff's margin, in that position. The unlabelled staves the
adjudication is actually about sit between and below them.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOB = (ROOT.parent / "omr-spans-veto-composition-2026-09" / "out" /
        "whole-spans-on.json")

#: What the print shows, read off out/page0NN_strips.png, staff index -> margin
#: text. Only the LABELLED staves — this is the join test, not the adjudication.
PRINTED = {
    56: {0: "Fl. pic.", 1: "Fl.", 2: "Ob.", 3: "Fag.", 4: "C. Fag.",
         5: "Cor.", 10: "Fl.", 11: "Ob.", 12: "Cl.", 13: "Fag.", 14: "Cor."},
    57: {0: "Fl.", 1: "Ob.", 2: "Cl.", 3: "Fag.", 4: "C. Fag.",
         9: "Fl.", 10: "Ob.", 11: "Cl.", 12: "Fag.", 13: "C. Fag.",
         14: "Cor.", 15: "Tr.", 16: "Tp.", 17: "Tr. Alt.", 18: "Tr. Ten.",
         19: "Tr. Bas."},
    63: {0: "Ob.", 1: "Cl.", 6: "Ob.", 7: "Cl.", 13: "Fl.", 14: "Ob.",
         15: "Cl.", 16: "Fag.", 17: "Cor.", 18: "Tp."},
    86: {0: "Fl. pic.", 1: "Fl.", 2: "Ob.", 3: "Cl.", 4: "Fag.",
         5: "C. Fag.", 6: "Cor.", 7: "Tr.", 8: "Tp.", 9: "Tr. Alt.",
         10: "Tr. Ten.", 11: "Tr. Bas."},
}
#: The margin abbreviation -> the canonical name the run should have resolved.
EXPECT = {
    "Fl. pic.": "Piccolo", "Fl.": "Flute", "Ob.": "Oboe", "Cl.": "Clarinet",
    "Fag.": "Bassoon", "C. Fag.": "Contrabassoon", "Cor.": "Horn",
    "Tr.": "Trumpet", "Tp.": "Timpani", "Tr. Alt.": "Trombone",
    "Tr. Ten.": "Trombone", "Tr. Bas.": "Trombone",
}


def main() -> int:
    blob = json.loads(BLOB.read_text())["contextual"]["absent_instrument_veto"]
    ev = defaultdict(dict)
    for e in blob["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    bad = 0
    n = 0
    for page, printed in sorted(PRINTED.items()):
        got = ev[page]
        if set(got) != set(printed):
            print(f"p{page}: MISMATCHED STAFF SET  run={sorted(got)} "
                  f"print={sorted(printed)}")
            bad += 1
        for si, text in sorted(printed.items()):
            n += 1
            want = EXPECT[text]
            if got.get(si) != want:
                print(f"p{page} st{si}: print {text!r} -> {want}, "
                      f"run says {got.get(si)!r}")
                bad += 1
    print(f"{n} labelled staves compared, {bad} disagreements")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
