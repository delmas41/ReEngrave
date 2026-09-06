"""Where the full-system identity errors are, page by page."""
from __future__ import annotations
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from score_full_systems import LINEUPS, systems, truth_for   # noqa: E402

work, path = sys.argv[1], sys.argv[2]
r = json.load(open(path))
rows = [(p, s, st, truth_for(work, p, len(st))) for p, s, st in systems(r)]
rows = [t for t in rows if t[3]]
n = sum(len(st) for _, _, st, _ in rows)
print(f"INPUT ASSERTION: full systems={len(rows)} staff-records={n}")
if not n:
    print("REFUSING: nothing scored")
    raise SystemExit(1)
for p, s, st, names in rows:
    bad = [(i, names[i], x.get("instrument")) for i, x in enumerate(st)
           if x.get("instrument") != names[i]]
    real = [b for b in bad if not (b[1] == "Contrabass" and b[2] == "Bass voice")]
    if real:
        print(f"  p{p}.s{s} ({len(st)} staves): " +
              "; ".join(f"ord{i} truth={w} got={g}" for i, w, g in real))
print()
print("(the Contrabass -> Bass voice lexicon fault is excluded above; it fires "
      "on the bottom staff of every full system)")
