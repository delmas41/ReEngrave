"""2.251 carry, exploration: rank fdots_explore.py output by body score; KNOWN (claimed F) vs the rest.

python3 work-2.251/rank_fx.py FX.txt [N]
"""
import ast, sys

rows = []
for l in open(sys.argv[1]):
    if l.startswith("templates") or l.startswith("page"):
        continue
    a = l.rstrip("\n").split(" ", 7)
    d = ast.literal_eval(a[7])
    rows.append((d["score"], d["cover"], d["extra"], d.get("scale"), " ".join(a[:6])))
rows.sort(reverse=True)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
print(len(rows), "pairs")
for r in rows[:n]:
    print(r)
print("KNOWN", sorted(r[0] for r in rows if "KNOWN" in r[4]))
