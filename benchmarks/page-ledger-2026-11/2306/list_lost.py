"""2306 r6: list notes written OFF and not ON, and eighth -> quarter, with the verdicts that changed and the reader of the ON stem row.
Usage: list_lost.py DIAGPREFIX STEMROWS.txt [FATESPREFIX]"""
import sys, json, collections
pre, rows = sys.argv[1], sys.argv[2]
fpre = sys.argv[3] if len(sys.argv) > 3 else None
rd = {l.split()[0]: l.split()[2] for l in open(rows)}
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
FB = json.load(open(fpre + ".on.json"))["fates"] if fpre else {}


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg") and h.get("kind") == "note":
            o[h["rg"]].append(h)
    return o


HA, HB = hosts(A), hosts(B)
V = [collections.defaultdict(dict), collections.defaultdict(dict)]
for i, D in enumerate((A, B)):
    for v in D["verdicts"]:
        if v["q"] in ("duration", "head_stem", "stem_value", "stem_direction"):
            V[i][v["s"]][v["q"]] = v
f = lambda v, q: v.get(q) and "%s/%s:%s" % (v[q]["o"], v[q]["r"], str(v[q]["v"])[:30])
for g in sorted(HA):
    lost = g not in HB
    q = (not lost) and any(h.get("type") == "eighth" for h in HA[g]) and all(h.get("type") == "quarter" for h in HB[g])
    if not (lost or q):
        continue
    a, b = V[0][g], V[1][g]
    hs = b.get("head_stem") or {}
    print(g, "LOST" if lost else "8->4", [(h.get("pitch"), h.get("type")) for h in HA[g]], "fate ON", FB.get(g), "| ON stem", hs.get("v"), rd.get(str(hs.get("v"))))
    for qq in ("head_stem", "stem_direction", "duration", "stem_value"):
        if f(a, qq) != f(b, qq):
            print("   ", qq, f(a, qq), "->", f(b, qq))
