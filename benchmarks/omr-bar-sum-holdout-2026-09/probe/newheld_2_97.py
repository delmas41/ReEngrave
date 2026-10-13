"""2.97 follow-up: why does a bar that added up in BASE hold in the ARM?
   python3 newheld_2_97.py BASE.pkl ARM.pkl BASE_REPORT.json ARM_REPORT.json OUT.json
For each newly held bar: every head whose standing duration verdict differs
(subject, decider, before -> after beats), and the bar length in force."""
import collections
import json
import pickle
import sys

sys.path.insert(0, ".")
from tools.omr.staged import consequences as C  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402
from tools.omr.staged.record import Outcome, Q  # noqa: E402

bl, al = (pickle.load(open(p, "rb")) for p in sys.argv[1:3])
br, ar = (json.load(open(p)) for p in sys.argv[3:5])


def held(r):
    return {(h["page"], h["system"], h["staff"], h["cell"]) for h in r["bars_held_out_sum"]["held"]}


new = sorted(held(ar) - held(br))


def desc(v):
    if v is None:
        return None
    if v.outcome is Outcome.DECIDED:
        return ("D", (v.value or {}).get("beats"), v.decider.split(":")[-1])
    if v.outcome is Outcome.NARROWED:
        return ("N", [c.value.get("beats") for c in v.candidates if isinstance(c.value, dict)], v.reason)
    return ("A", None, v.reason)


out = {}
cnt = collections.Counter()
for k in new:
    cell = R.cell(*k)
    rows = []
    for v in C._standing(al, cell, Q.DURATION):
        b = bl.verdict(Q.DURATION, v.subject)
        if desc(b) != desc(v):
            rows.append({"glyph": v.subject.glyph, "base": desc(b), "arm": desc(v)})
    meter = al.verdict(Q.METER, cell.at(R.Kind.SYSTEM))
    exp = C._bar_beats_at(meter, cell) if meter is not None and meter.outcome is Outcome.DECIDED else None
    kinds = sorted({(r["arm"][2] if r["arm"] else "-") for r in rows})
    cnt[tuple(kinds)] += 1
    out["/".join(map(str, k))] = {"expected": exp, "changed": rows}
for k, n in cnt.most_common():
    print(n, k)
print(len(new), "newly held bars")
json.dump(out, open(sys.argv[5], "w"), indent=1, default=str)
