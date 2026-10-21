"""2.185: join census.py + mech.py output and print the tables (markdown-ish). usage: tables.py CENSUS.json MECH.json [--rows OUT.json]"""
import json, sys, collections
r = json.load(open(sys.argv[1])); mech = json.load(open(sys.argv[2]))
ALIVE = ("kept", "unjudged")
rows = []
for c in r["clusters"]:
    k = ",".join(str(i) for i in sorted(m["i"] for m in c["members"]))
    ms = c["members"]
    fams = sorted({m["fam"] for m in ms}); cls = {m["cls"] for m in ms}
    kept = [m for m in ms if m["fate"] == "kept"]; unj = [m for m in ms if m["fate"] == "unjudged"]
    alive = kept + unj
    judged = len(ms) - len(unj)
    if not alive: out = "all_dead"
    elif len(alive) == 1: out = "one_alive"
    elif len(kept) >= 2: out = "multi_kept"
    elif len(kept) == 1: out = "one_kept+unjudged"
    else: out = "all_unjudged"
    cause = mech.get(k, "?")
    rows.append(dict(cause=cause, base=cause.split("+")[0], fam=fams[0] if len(fams) == 1 else "X:" + "+".join(fams),
                     ct="same_class" if len(cls) == 1 else ("diff_class" if len(fams) == 1 else "cross_family"),
                     out=out, judged=judged, n=len(ms), alive_cls=len({m["cls"] for m in alive}), refused=sum(m["fate"] == "refused" for m in ms),
                     given=sum(m["fate"] == "given_away" for m in ms), members=ms, key=k))
nb = sum(x["n"] for x in rows)
print("boxes %d (scorable %d); clusters %d; boxes in clusters %d = %.1f%% of all, %.1f%% of scorable" % (r["nbox_all"], r["nbox_scorable"], len(rows), nb, 100 * nb / r["nbox_all"], 100 * nb / r["nbox_scorable"]))
def tab(title, kf, filt=None, top=60):
    t = collections.Counter(); b = collections.Counter()
    for x in rows:
        if filt and not filt(x): continue
        t[kf(x)] += 1; b[kf(x)] += x["n"]
    print("\n##", title)
    for k, v in sorted(t.items(), key=lambda kv: -kv[1])[:top]: print("  %5d cl %5d bx  %s" % (v, b[k], k))
tab("cause", lambda x: x["cause"])
tab("cause x outcome  [clusters with >=1 judged member = reading-relevant]", lambda x: (x["base"], x["out"]), lambda x: x["judged"] > 0)
tab("all-unjudged clusters (structural: nothing adjudicates the class)", lambda x: (x["fam"], x["base"]), lambda x: x["judged"] == 0, top=15)
tab("cause x classtype", lambda x: (x["base"], x["ct"]))
tab("family/pair x outcome (relevant)", lambda x: (x["fam"], x["out"]), lambda x: x["judged"] > 0, top=80)
if "--rows" in sys.argv:
    json.dump(rows, open(sys.argv[sys.argv.index("--rows") + 1], "w"))
