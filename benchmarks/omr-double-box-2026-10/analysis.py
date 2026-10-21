"""2.185: tables from census.py output. usage: analysis.py CENSUS.json  (prints tables; pass --json OUT to dump the rows)"""
import json, sys, collections
r = json.load(open(sys.argv[1]))
CL = r["clusters"]
def kind(c):
    if c["cells"] == 1: return "same_cell"
    return "cross_cell_same_staff" if c["staffs"] == 1 else "cross_staff"
def classtype(c):
    cls = {m["cls"] for m in c["members"]}; fams = {m["fam"] for m in c["members"]}
    if len(cls) == 1: return "same_class"
    return "diff_class_same_family" if len(fams) == 1 else "cross_family"
ALIVE = ("kept", "unjudged")
def outcome(c):
    a = [m for m in c["members"] if m["fate"] in ALIVE]
    if not a: return "all_refused_or_given_away"
    if len(a) == 1: return "one_alive"
    return "multi_alive_same_class" if len({m["cls"] for m in a}) == 1 else "multi_alive_diff_class"
def srcs(c): return "+".join(sorted(m["src"] for m in c["members"]))
rows = [dict(kind=kind(c), ct=classtype(c), out=outcome(c), srcs=srcs(c), fams="+".join(sorted(m["fam"] for m in c["members"])), c=c) for c in CL]
nb = sum(len(c["members"]) for c in CL)
print("clusters", len(CL), "boxes in clusters", nb, "of all", r["nbox_all"], "(scorable", r["nbox_scorable"], ") = %.1f%%/%.1f%%" % (100*nb/r["nbox_all"], 100*nb/r["nbox_scorable"]))
def tab(title, keyf, filt=lambda x: True):
    t = collections.Counter(); b = collections.Counter()
    for x in rows:
        if filt(x): t[keyf(x)] += 1; b[keyf(x)] += len(x["c"]["members"])
    print("\n##", title)
    for k, v in sorted(t.items(), key=lambda kv: -kv[1]): print("  %5d clusters %5d boxes  %s" % (v, b[k], k))
tab("kind x classtype", lambda x: (x["kind"], x["ct"]))
tab("kind x outcome", lambda x: (x["kind"], x["out"]))
tab("outcome by classtype", lambda x: (x["ct"], x["out"]))
tab("source combos", lambda x: x["srcs"], lambda x: x["srcs"] != "prod+prod")
if "--json" in sys.argv:
    json.dump([{k: v for k, v in x.items()} for x in rows], open(sys.argv[sys.argv.index("--json") + 1], "w"))
