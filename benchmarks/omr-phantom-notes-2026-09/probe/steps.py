"""WHERE ON THE STAFF does the lone note stand? -- the decisive cheap test.

⚠️ A WHOLE REST HANGS UNDER THE FOURTH LINE FROM THE BOTTOM and the engraver
has no freedom about it. With the bottom line step 0 and one step per HALF
staff space, the rectangle's body runs from step 6 down to step 5, so ink
centred on it resolves to step 5 or 6 -- `C5` or `D5` in treble, and the
transposed equivalent under any other clef. So if Sean's lone notes are whole
rests read as noteheads, their STAFF STEP must pile up at 5-6; if they are
ordinary music that survived while its neighbours were held back, it must look
like the page's own note distribution.

⚠️ This asks the EXPORTED FILE only. It needs no weights, no record and no
detector -- the pitch and the clef are both in the artefact, and a staff step
is arithmetic on the two. The NULL is the file's own 21,000-odd other notes,
which is what makes a pile-up mean anything.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from locate import SYSMAP, index  # noqa: E402
from population import ARTEFACT, bars  # noqa: E402

LETTER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
#: The diatonic number of each clef's BOTTOM LINE. `dn = octave*7 + letter`.
BOTTOM_LINE = {
    "treble": 4 * 7 + LETTER["E"],   # E4
    "bass": 2 * 7 + LETTER["G"],     # G2
    "alto": 3 * 7 + LETTER["F"],     # F3
    "tenor": 3 * 7 + LETTER["D"],    # D3
}
#: The two steps a whole rest's ink occupies (5 = the space's middle, 6 = the
#: line it hangs from). NOT a tuned window -- it is the engraving convention.
REST_STEPS = (5, 6)


def step_of(pitch, clef):
    if not pitch or clef not in BOTTOM_LINE:
        return None
    letter, octave = pitch[0], int(pitch[1:])
    return octave * 7 + LETTER[letter] - BOTTOM_LINE[clef]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xml", default=str(ARTEFACT))
    ap.add_argument("--sysmap", default=str(SYSMAP))
    ap.add_argument("--json-out")
    a = ap.parse_args()

    where, _ = index(json.loads(Path(a.sysmap).read_text()))
    rows = bars(a.xml)

    lone, other = [], []
    for r in rows:
        w = where.get((r["part"], r["number"]))
        clef = (w or {}).get("clef")
        is_lone = r["n_notes"] == 1 and r["n_pitched"] == 1
        for e in r["events"]:
            if not e["pitch"]:
                continue
            s = step_of(e["pitch"], clef)
            if s is None:
                continue
            rec = dict(part=r["part"], measure=r["number"], pitch=e["pitch"],
                       clef=clef, step=s, dur=e["dur"], type=e["type"],
                       barlen=r["barlen"])
            (lone if is_lone else other).append(rec)

    if not lone or not other:
        print("DEAD: one of the two populations is empty", file=sys.stderr)
        return 2

    under = [r for r in lone if r["dur"] and r["barlen"] and r["dur"] < r["barlen"]]
    quarter = [r for r in under if r["dur"] == 96 and r["barlen"] == 192]
    full = [r for r in lone if not (r["dur"] and r["barlen"] and r["dur"] < r["barlen"])]

    pops = [("EVERY OTHER NOTE IN THE FILE (the null)", other),
            ("lone-pitched bar, FULL length", full),
            ("lone-pitched bar, UNDERFULL", under),
            ("lone QUARTER in a 2/4 bar (Sean's population)", quarter)]

    print(f"REACH  notes with a resolvable staff step: "
          f"{len(other) + len(lone)}  (null {len(other)}, lone {len(lone)})")
    print()
    hdr = f"{'population':<46}{'n':>6}{'at step 5-6':>13}{'share':>9}"
    print(hdr)
    print("-" * len(hdr))
    out = {}
    for name, pop in pops:
        hit = sum(1 for r in pop if r["step"] in REST_STEPS)
        share = hit / len(pop) if pop else 0.0
        out[name] = dict(n=len(pop), at_rest_step=hit, share=round(share, 4))
        print(f"{name:<46}{len(pop):>6}{hit:>13}{share:>9.3f}")

    print()
    for name, pop in pops:
        c = collections.Counter(r["step"] for r in pop)
        top = ", ".join(f"{s}:{n}" for s, n in sorted(c.items()))
        print(f"{name}\n   step histogram: {top}")
        print()

    print("=== the lone quarters, one line each")
    for r in sorted(quarter, key=lambda r: (int(r['part'][1:]), int(r['measure']))):
        mark = "  <-- REST SLOT" if r["step"] in REST_STEPS else ""
        print(f"  {r['part']:>4} m{r['measure']:<4} {r['pitch']:<4} "
              f"clef={str(r['clef']):<7} step={r['step']:<4}{mark}")

    if a.json_out:
        Path(a.json_out).write_text(json.dumps(
            dict(summary=out, quarter=quarter, under=under, lone=lone), indent=1))
        print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
