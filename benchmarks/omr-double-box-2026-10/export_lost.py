"""2.185: Litolff, heads and rests: of the inks with ZERO boxes written by the real exporter, which were lost to the duplicate rules?
usage: export_lost.py ROWS.json FATES.json"""
import json, sys, collections
rows = json.load(open(sys.argv[1])); fates = json.load(open(sys.argv[2]))
W = ("written", "written_relocated")
DUP = ("stacked_head_duplicate", "notehead_is_a_duplicate_box", "mark_group_duplicate", "rest_is_a_duplicate_box", "is_a_rest_twin")
OWN = ("owned_by_another_staff",)
c = collections.Counter(); ink = collections.Counter()
for x in rows:
    tr = [m for m in x["members"] if m["subject"] in fates]
    if not tr: continue
    fam = "head" if all(m["cls"].startswith("notehead") for m in tr) else ("rest" if all(m["cls"].startswith("rest") for m in tr) else "head+rest")
    fs = [fates[m["subject"]] for m in tr]
    nw = sum(f in W for f in fs)
    ink[(fam, "written>=1" if nw else "written=0")] += 1
    if nw == 0:
        dup = any(any(d in f for d in DUP) for f in fs)
        allowed = all(any(d in f for d in DUP + OWN) for f in fs)
        k = "lost: only duplicate/owner refusals, >=1 duplicate-type" if (dup and allowed) else ("lost: duplicate-type refusal plus another reason" if dup else "lost: no duplicate-type reason (other reasons)")
        c[(fam, k)] += 1
for k, v in sorted(ink.items()): print(v, k)
print()
for k, v in sorted(c.items()): print(v, k)
