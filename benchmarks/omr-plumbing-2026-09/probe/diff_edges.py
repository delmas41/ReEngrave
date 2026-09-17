"""Two edge tables, one diff — what a change did to the CONNECTIONS."""
import json, sys, collections
a = json.loads(open(sys.argv[1]).read()); b = json.loads(open(sys.argv[2]).read())
A = {(r["producer"], r["consumer"]): r["state"] for r in a["rows"]}
B = {(r["producer"], r["consumer"]): r["state"] for r in b["rows"]}
print(f"BEFORE {len(A)} edges   AFTER {len(B)} edges")
new = sorted(set(B) - set(A)); gone = sorted(set(A) - set(B))
moved = sorted(k for k in set(A) & set(B) if A[k] != B[k])
print(f"\n── NEW EDGES ({len(new)})")
for k in new: print(f"   {k[0]:26} → {k[1]:42} {B[k]}")
print(f"\n── EDGES THAT DISAPPEARED ({len(gone)})")
for k in gone: print(f"   {k[0]:26} → {k[1]:42} was {A[k]}")
print(f"\n── STATE CHANGED ({len(moved)})")
for k in moved: print(f"   {k[0]:26} → {k[1]:42} {A[k]} -> {B[k]}")
for tag, t in (("BEFORE", a), ("AFTER", b)):
    print(f"\n{tag} summary: {t['summary']}")
