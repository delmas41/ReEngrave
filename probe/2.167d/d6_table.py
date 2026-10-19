"""2.167d probe 6: cause x plate table from data/<plate>_items_analysed.json, plus second-pass recovery. usage: d6_table.py"""
import collections
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/data/"
VAR = ["shiftR", "shiftL", "wide", "system"]


def cause(o):
    st, k, w = o["stage"], o["kind"], o["what"].lower()
    if "[in neighbour cell]" in st:
        return "F. boxed, but in the NEIGHBOUR cell (crop edge)"
    if k == "extra":
        if "chord" in w and ("second" in w or "two events" in w or "split" in w):
            return "G. extra: one chord counted as two events (EVALUATE grouping)"
        if "twice" in w or "two rests" in w:
            return "H. extra: one ink boxed twice, both written"
        return "E. extra: non-note ink boxed as a note/rest and written"
    if "never boxed" in st:
        return "A. never boxed (no box >= 0.05)"
    if "under the 0.25 floor" in st:
        return "B. boxed right class, UNDER the 0.25 floor" if "wrong class" not in st else "C. boxed in the WRONG class"
    if "dropped by gate: rest:decided/rest_has_a_stem" in st:
        return "C. boxed in the WRONG class"
    if "(other)" in st:
        return "C. boxed in the WRONG class"
    if "(rest) , value" in st or "(rest), value" in st:
        return "D. boxed right, a later gate dropped / mis-valued it"
    if "dropped by gate" in st or "value not applied" in st or "other" in st:
        return "D. boxed right, a later gate dropped / mis-valued it"
    return "?"


rows = []
for pl in ("lit", "bra"):
    d = json.load(open(D + "%s_items_analysed.json" % pl))
    for o in d["items"]:
        o["cause"] = cause(o)
        rows.append(o)
C = collections.defaultdict(lambda: collections.Counter())
Cb = collections.defaultdict(lambda: collections.defaultdict(set))
for o in rows:
    C[o["cause"]][o["plate"]] += 1
    Cb[o["cause"]][o["plate"]].add(o["bar"])
print("cause | Litolff items (bars) | Brahms items (bars) | all")
for c in sorted(C):
    l, b = C[c]["lit"], C[c]["bra"]
    print("%-62s %3d (%2d)  %3d (%2d)  %3d" % (c, l, len(Cb[c]["lit"]), b, len(Cb[c]["bra"]), l + b))
print("total items", len(rows), "lit", sum(C[c]["lit"] for c in C), "bra", sum(C[c]["bra"] for c in C))
# sub-detail of C and D
for c in ("C. boxed in the WRONG class", "D. boxed right, a later gate dropped / mis-valued it"):
    print("\n", c)
    sub = collections.Counter((o["plate"], o["stage"][:60]) for o in rows if o["cause"] == c)
    for k, v in sub.most_common():
        print("  ", v, k)
# crop edge
print("\nEDGE (distance of the item's box centre from the nearer cell edge, spaces) for causes A,B,C,D (items that are lost real symbols)")
for c in sorted(C):
    if c[0] in "ABCD":
        es = [o["edge_sp"] for o in rows if o["cause"] == c]
        cr = sum(1 for o in rows if o["cause"] == c and o["crosses_edge"])
        near = sum(1 for e in es if e < 1.0)
        print("%-62s n=%d  <1sp from an edge: %d  box crosses the cell edge: %d  median %.1f sp" % (c, len(es), near, cr, sorted(es)[len(es) // 2]))
# recovery
print("\nSECOND PASS RECOVERY (a box >= 0.25 of the wanted family at the item spot, same weights)")
for c in sorted(C):
    if c[0] in "ABC":
        it = [o for o in rows if o["cause"] == c and o["found"]]
        if not it:
            continue
        cnt = {v: sum(1 for o in it if o["found"].get(v)) for v in VAR}
        anyv = sum(1 for o in it if any(o["found"].get(v) for v in VAR))
        print("%-62s n=%d  %s  any=%d" % (c, len(it), cnt, anyv))
        for pl in ("lit", "bra"):
            it2 = [o for o in it if o["plate"] == pl]
            if it2:
                print("      %s n=%d %s any=%d" % (pl, len(it2), {v: sum(1 for o in it2 if o["found"].get(v)) for v in VAR}, sum(1 for o in it2 if any(o["found"].get(v) for v in VAR))))
json.dump(rows, open(D + "items_all.json", "w"), indent=1)
