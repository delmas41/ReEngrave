"""2.197 C9: truth-free funnel of the accidental-/key-class boxes of one view: box class -> accidental_staff_position row? -> owner outcome/reason -> written
<accidental>/alter on the owner head. usage: c9_funnel.py VIEW.json XML OUT.json"""
import sys, json, collections
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, fam, ALT
v = View(sys.argv[1], sys.argv[2])
F = collections.Counter(); per = collections.defaultdict(collections.Counter)
for pg, bs in v.boxes.items():
    for g in bs:
        if g["reader"] != "detector" or not fam(g["cls"]): continue
        cls = g["cls"]; role = "cell0" if g["cell"] == 0 else "later"
        if fam(cls) == "key":
            per[(cls, role)]["boxes"] += 1
            per[(cls, role)]["no accidental row (key class: never an accidental)"] += 1
            continue
        P = per[(cls, role)]; P["boxes"] += 1
        row = v.accpos.get(g["key"])
        if not row: P["no_row"] += 1; continue
        dt = row.get("detail") or {}
        if dt.get("one_ink_absorbed"): P["absorbed_by_a_stronger_class_of_the_same_ink (2.186)"] += 1; continue
        own = v.verdict(g["key"], "accidental_owner")
        if own is None: P["no_owner_verdict"] += 1; continue
        if own["outcome"] == "decided":
            P["owner_decided"] += 1
            xn = v.xml_notes.get(own["value"])
            alt = (own.get("detail") or {}).get("alteration") or dt.get("alteration"); want = {"b": "flat", "#": "sharp", "n": "natural", "natural": "natural", "##": "double-sharp", "bb": "flat-flat"}.get(alt)
            if xn is None: P["decided_but_head_not_written"] += 1
            elif xn["accidental"] == want: P["written_as_<accidental>"] += 1
            elif xn["accidental"] is None: P["decided_head_written_WITHOUT_accidental_elem"] += 1
            else: P["decided_head_written_with_OTHER_accidental"] += 1
        else:
            P["abstained:" + str(own["reason"])] += 1
json.dump({"%s|%s" % k: dict(c) for k, c in per.items()}, open(sys.argv[3], "w"), indent=1)
tot = collections.Counter()
for k, c in sorted(per.items()):
    print(k, dict(c))
    for a, b in c.items(): tot[a] += b
print("TOTAL", dict(tot))
