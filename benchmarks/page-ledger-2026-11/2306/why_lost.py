"""2306 r6: for every note written OFF and not ON (and eighth -> quarter) on the replayed pages: the head's own ADJUDICATE duration reading (first
duration verdict) and the final one both arms, the strokes the ON reading refused that OFF did not (by rule), the ON stem row's reader, EXPORT's fate
ON; grouped. Usage: why_lost.py RFPREFIX STEMROWS.txt [--show g,g]"""
import sys, json, collections
pre, rowsf = sys.argv[1], sys.argv[2]
show = sys.argv[sys.argv.index("--show") + 1].split(",") if "--show" in sys.argv else []
rd = {l.split()[0]: l.split()[2] for l in open(rowsf)}
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
VA, VB = collections.defaultdict(lambda: collections.defaultdict(list)), collections.defaultdict(lambda: collections.defaultdict(list))
for D, V in ((A, VA), (B, VB)):
    for v in D["verdicts"]:
        V[v["s"]][v["q"]].append(v)


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg") and h.get("kind") == "note":
            o[h["rg"]].append(h)
    return o


HA, HB = hosts(A), hosts(B)
FA, FB = A.get("fates") or {}, B.get("fates") or {}
sig = lambda v: v and "%s/%s%s" % (v["o"], v["r"], ":%s" % (v["v"] or {}).get("written") if isinstance(v["v"], dict) else "")


def refused(v):
    return collections.Counter(r["why"] for r in (((v or {}).get("d") or {}).get("refused_strokes") or []))


def last(V, g, q):
    l = V[g].get(q)
    return l[-1] if l else None


def firstv(V, g, q):
    l = V[g].get(q)
    return l[0] if l else None


lost, quarter = [], []
for g, hs in HA.items():
    if g not in HB:
        lost.append(g)
    elif any(h.get("type") == "eighth" for h in hs) and all(h.get("type") == "quarter" for h in HB[g]):
        quarter.append(g)
allrows = []
for name, gs in (("LOST", lost), ("EIGHTH->QUARTER", quarter)):
    c = collections.Counter()
    for g in sorted(gs):
        a1, b1 = firstv(VA, g, "duration"), firstv(VB, g, "duration")
        hs = last(VB, g, "head_stem")
        hsa = last(VA, g, "head_stem")
        stem_on = hs and hs["o"] == "decided" and rd.get(str(hs["v"]))
        same_stem = bool(hs and hsa and hs["v"] == hsa["v"])
        newref = refused(b1) - refused(a1)
        own_reading = "own reading same" if sig(a1) == sig(b1) else "own reading %s -> %s" % (sig(a1), sig(b1))
        key = (own_reading, "ON stem %s%s" % (stem_on or (hs and sig(hs)), " (same row)" if same_stem else ""),
               "ON-only refusals %s" % (dict(newref) or "-"), "fate %s" % FB.get(g, "?"))
        c[key] += 1
        allrows.append((name, g, key, sig(last(VA, g, "duration")), sig(last(VB, g, "duration"))))
    print("%s: %d" % (name, len(gs)))
    for k, n in c.most_common():
        print("  %3d  %s" % (n, " | ".join(k)))
print()
for name, g, k, la, lb in allrows:
    print(name, g, "| final", la, "->", lb, "|", " | ".join(k))
for g in show:
    print("==", g, "OFF", [(h.get("pitch"), h.get("type")) for h in HA.get(g, [])], "ON", [(h.get("pitch"), h.get("type")) for h in HB.get(g, [])],
          "fate", FA.get(g), "->", FB.get(g))
    for q in sorted(set(VA[g]) | set(VB[g])):
        a, b = VA[g].get(q), VB[g].get(q)
        if json.dumps(a, sort_keys=True, default=str) != json.dumps(b, sort_keys=True, default=str):
            for i in range(max(len(a or []), len(b or []))):
                x = (a or [None] * 9)[i] if a and i < len(a) else None
                y = (b or [None] * 9)[i] if b and i < len(b) else None
                print("  ", q, i, "\n     OFF", json.dumps(x and {k: x.get(k) for k in ("o", "r", "v", "d")}, default=str)[:1200],
                      "\n     ON ", json.dumps(y and {k: y.get(k) for k in ("o", "r", "v", "d")}, default=str)[:1200])
