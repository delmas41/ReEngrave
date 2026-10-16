"""2.152 A -- reach table from analyze_tiles.py rows. usage: summarize_tiles.py ROWS.json [--list]"""
import json
import sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1]))
if "--sel-other" in sys.argv:
    rows = [r for r in rows if r.get("sel") == "other"]
ERR = {"phantom_head", "phantom_rest", "rest_as_head", "value_error", "lost_note", "lost_rest", "rest_for_note"}
RIGHT = {"right"}
FACTS = [("P1p3", lambda r: r.get("p1_3")), ("P1p4", lambda r: r.get("p1_4")), ("P1p5", lambda r: r.get("p1_5")),
         ("P1doc4", lambda r: r.get("p1doc_4")),
         ("S1v", lambda r: r.get("s1_v")), ("S1h", lambda r: r.get("s1_h")), ("S1n", lambda r: r.get("s1_n")),
         ("S1any", lambda r: any(r.get("s1_" + k) for k in "vhn") if "s1_v" in r else None),
         ("S2a1", lambda r: r.get("s2a_1")), ("S2a1.5", lambda r: r.get("s2a_1.5")), ("S2a3", lambda r: r.get("s2a_3")),
         ("S2b", lambda r: r.get("s2b")),
         ("F148", lambda r: r.get("f148")), ("F150", lambda r: r.get("f150")),
         ("ANYstrict", lambda r: bool(r.get("p1_4") or r.get("s1_h") or r.get("s2b"))),
         ("ANYloose", lambda r: bool(r.get("p1_4") or r.get("s1_v") or r.get("s1_h") or r.get("s1_n") or r.get("s2a_1.5") or r.get("s2b")))]


def cell(rs, f):
    ev = [f(r) for r in rs]
    ok = [e for e in ev if e is not None]
    return "%d/%d" % (sum(1 for e in ok if e), len(ok)) + ("" if len(ok) == len(ev) else " (n/a %d)" % (len(ev) - len(ok)))


groups = defaultdict(list)
for r in rows:
    d = r["doc"]
    st = r["status"]
    if st in ERR:
        groups[(d, "ERR:" + st)].append(r)
        groups[(d, "ERR:all")].append(r)
        groups[("all", "ERR:" + st)].append(r)
        groups[("all", "ERR:all")].append(r)
    elif st in RIGHT:
        groups[(d, "RIGHT")].append(r)
        groups[("all", "RIGHT")].append(r)
print("status census:", Counter((r["doc"], r["status"]) for r in rows).most_common())
hdr = ["group", "n"] + [n for n, _ in FACTS]
print("\t".join(hdr))
for (d, g), rs in sorted(groups.items()):
    print("\t".join([d + " " + g, str(len(rs))] + [cell(rs, f) for _, f in FACTS]))
if "--list" in sys.argv:
    for r in rows:
        if r["status"] in ERR:
            print(r["doc"], r["item"], r["n"], r["glyph"], r["status"], "sean=", r["sean"], r.get("cls"), "w,h=", r.get("w"),
                  r.get("h"), "vd", r.get("vd"), "p1", r.get("p1_detail"), "s1", [r.get("s1_" + k) for k in "vhn"],
                  "s2", r.get("s2a_1.5"), r.get("s2b"), r.get("s2_nev"), r.get("s2_nhdr"))
