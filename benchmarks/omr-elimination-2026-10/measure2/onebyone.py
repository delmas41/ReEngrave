"""(WHY the tie/beam widenings are ALTERNATIVE envelopes, not global) Each round-1-failure widening ALONE as a GLOBAL bound: marks whose set gains the symbol (cost) vs true marks recovered (benefit). Uses truth2_rows.json."""
import json, sys, copy
sys.path.insert(0, ".")
import table2 as T2
rows = json.load(open("measure2/truth2_rows.json"))
base = T2.build(widen=False, detector=False, litolff=False)
def run(S):
    return [set(T2.candidates(r["d"], S)[0]["all"]) for r in rows]
b = run(base); b_ok = sum(r["sym"] in s for r, s in zip(rows, b))
print("baseline (Sean only): survive", b_ok)
import re
steps = [("dynamic_letter", "env1", 14.29), ("tie", "fill1", 0.83), ("tie", "env3", 2.75), ("barline", "fill0", 0.11),
         ("barline", "env2", 1.22), ("flag", "env1", 2.37), ("beam", "env2", 0.20)]
for name, field, val in steps:
    S = copy.deepcopy(base); s = S[name]
    if field.startswith("env"): i = int(field[3]); e = list(s["env"]); e[i] = val; s["env"] = tuple(e)
    else: i = int(field[4]); f = list(s["fill"]); f[i] = val; s["fill"] = tuple(f)
    a = run(S)
    gained = sum(name in x and name not in y for x, y in zip(a, b))
    rec = sum(r["sym"] in x and r["sym"] not in y for r, x, y in zip(rows, a, b))
    print("%-15s %-5s -> %-6s  marks gaining '%s' in set: %4d | true marks recovered: %d" % (name, field, val, name, gained, rec))
