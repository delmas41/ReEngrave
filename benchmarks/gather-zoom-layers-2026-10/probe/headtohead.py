"""2.152 -- P1 (page census) vs the fixed cut-offs already in the tree (2.148 head-sized window; 2.150 quarter-rest width
floor), on the SAME Sean-judged boxes; plus the 2.150 width ladder. usage: headtohead.py ROWS.json"""
import json
import sys

rows = json.load(open(sys.argv[1]))
ERR = {"phantom_head", "rest_as_head", "value_error", "lost_note", "lost_rest", "phantom_rest"}


def tab(title, rs):
    e = [r for r in rs if r["status"] in ERR]
    ok = [r for r in rs if r["status"] == "right"]
    print("== %s   errors %d, right readings %d" % (title, len(e), len(ok)))
    for name, f in (("P1 page z>4", "p1_4"), ("P1 doc z>4", "p1doc_4"), ("fixed 2.148 window", "f148"), ("fixed 2.150 floor", "f150")):
        ee = [r[f] for r in e if r.get(f) is not None]
        oo = [r[f] for r in ok if r.get(f) is not None]
        if ee or oo:
            print("   %-20s errors %d/%d   right %d/%d" % (name, sum(ee), len(ee), sum(oo), len(oo)))
    both = [r for r in e if r.get("p1_4") is not None and r.get("f148") is not None]
    print("   head-class errors with both: P1 only %d, fixed only %d, both %d, neither %d" % (
        sum(1 for r in both if r["p1_4"] and not r["f148"]), sum(1 for r in both if r["f148"] and not r["p1_4"]),
        sum(1 for r in both if r["f148"] and r["p1_4"]), sum(1 for r in both if not r["f148"] and not r["p1_4"])))


heads = [r for r in rows if r.get("cat") == "notehead"]
tab("head-class boxes, all galleries", heads)
tab("head-class boxes, size-blind selection (sel=other)", [r for r in heads if r["sel"] == "other"])
tab("head-class, Litolff", [r for r in heads if r["doc"] == "litolff"])
tab("head-class, Brahms (night+p0p3)", [r for r in heads if r["doc"] != "litolff"])
print("\n2.150 width ladder (Sean's word; z = page-census robust z of the width)")
for r in sorted([r for r in rows if r["item"] == "2.150"], key=lambda r: r["w"]):
    print("  w=%.2f sp  h=%.2f  %-14s %-9s z_w=%s  F150(<0.7)=%s" % (
        r["w"], r["h"], r["sean"], r["doc"], (r.get("p1_detail") or {}).get("w", [None, None])[1], r.get("f150")))
