"""DOES THE PHYSICAL GATE EXPLAIN THE DISAGREEMENTS?

Where the convention and the shipped beam-mate tier BOTH speak on a head
neither could read from its own stem, they agree 97.0% on Litolff and only
84.7% on Breitkopf. One of the two is wrong on those heads and no instrument in
this repo can say which -- no note in any stem arm has ever been checked
against the print.

⚠️ THIS IS THE ONE TEST THAT CAN MOVE THE QUESTION WITHOUT A CROP. If the
disagreements sit OUTSIDE the physical run-length gate -- shorter than the
shortest component `detect_stems` would call a stem, or longer than
`STEM_MAX_HEIGHT_LINES`, which its own comment says is *"a barline"* -- then
the convention is the party at fault there and the gate is the repair. If they
sit INSIDE it, the gate does not rescue the convention and the disagreement is
a genuine unresolved contest between two readings.

⚠️ It cannot tell us the convention is RIGHT inside the gate. It can only tell
us whether the gate is where the trouble lives.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from tools.omr.line_detection import STEM_MAX_HEIGHT_LINES      # noqa: E402

GATE_LO, GATE_HI = 2.0, STEM_MAX_HEIGHT_LINES
OUT = HERE / "out"


def main() -> int:
    any_rows = False
    for label, tag in (("Litolff Beethoven 5 pp.1-4", "litolff"),
                       ("Breitkopf Brahms 1 pp.0-3", "breitkopf")):
        rp, bp = OUT / f"{tag}-rows.json", OUT / f"{tag}-beammate.json"
        if not rp.is_file() or not bp.is_file():
            print(f"skipping {label}: missing an input", file=sys.stderr)
            continue
        rows = {r["subject"]: r
                for r in json.loads(rp.read_text())["rows"]}
        fired = json.loads(bp.read_text())["fired"]
        c: collections.Counter = collections.Counter()
        for s, d in fired.items():
            r = rows.get(s)
            if not r or not r["says"]:
                continue
            arm = max(r["R_up"], r["L_down"])
            gate = ("in" if GATE_LO <= arm <= GATE_HI else "OUT")
            c[(gate, "agree" if r["says"] == d else "disagree")] += 1
            any_rows = True
        print(f"== {label} -- the convention against the shipped tier, "
              f"split by the gate [{GATE_LO:g}, {GATE_HI:g}] spaces")
        for g in ("in", "OUT"):
            ok, no = c[(g, "agree")], c[(g, "disagree")]
            t = ok + no
            print(f"   {g:>3} the gate   n={t:>4}   agree {ok:>4}   "
                  f"disagree {no:>3}" + (f"   {ok/t:>6.1%}" if t else ""))
        tot_d = c[("in", "disagree")] + c[("OUT", "disagree")]
        if tot_d:
            print(f"   -> {c[('OUT','disagree')]}/{tot_d} of the "
                  f"disagreements sit OUTSIDE the gate")
        print()
    if not any_rows:
        print("DEAD: no head had both mechanisms speak", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
