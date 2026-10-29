"""2.229: Sean's judged answers, scored on the OLD record and the NEW record, matched per tile (item, tile) on the frozen-sample pages.
right->wrong must be 0. usage: judged_diff.py OLD.json NEW.json PAGES"""
import json, sys, collections
old, new = (json.load(open(p)) for p in sys.argv[1:3])
pages = {int(x) for x in sys.argv[3].split(",")}
SC = ("right", "wrong", "narrowed", "abstained")
def idx(d):
    return {(t["item"], t["tile"]): t for t in d["tiles"]}
O, N = idx(old), idx(new)
def pg(t):
    s = t["subject"]
    s = s[0] if isinstance(s, list) and s else s
    return int(s.split("/")[1]) if isinstance(s, str) and s.startswith(("glyph/", "cell/")) else None
trans = collections.Counter(); rw = []
for k, t in N.items():
    o = O.get(k)
    if pg(t) not in pages: continue
    if o is None: trans[("(absent)", t["status"])] += 1; continue
    trans[(o["status"], t["status"])] += 1
    if o["status"] == "right" and t["status"] == "wrong": rw.append((k, t["subject"], t["answer"], t["note"]))
sc_old = collections.Counter(O[k]["status"] for k, t in N.items() if k in O and pg(t) in pages)
sc_new = collections.Counter(t["status"] for k, t in N.items() if pg(t) in pages)
print("frozen-sample-page tiles: old", {s: sc_old[s] for s in SC}, " new", {s: sc_new[s] for s in SC})
for (a, b), n in sorted(trans.items(), key=lambda x: -x[1]):
    if a in SC or b in SC: print("  %-10s -> %-10s %d" % (a, b, n))
print("right->wrong:", len(rw))
for r in rw: print("  ", r)
wr = [(k, t["subject"], t["answer"]) for k, t in N.items() if t["status"] == "wrong" and pg(t) in pages]
print("wrong now (frozen pages):", len(wr))
