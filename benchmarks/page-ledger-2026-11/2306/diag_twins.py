"""Is the change in a bar carried by heads OWNED BY ANOTHER STAFF (padded-cell twins) that gained a stem direction? Per new red bar, lost tie, lost
flag, gained rest: does the bar hold (a) a twin head whose stem_direction changed, (b) a head of this staff whose stem_direction changed, (c) an event
/ voices change. Usage: diag_twins.py PREFIX [--pages ...]"""
import sys, json, collections
pre = sys.argv[1]
pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")} if "--pages" in sys.argv else None
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))


def idx(D):
    by = collections.defaultdict(dict)
    for v in D["verdicts"]:
        p = v["s"].split("/")
        if p[0] in ("glyph", "cell") and len(p) >= 5:
            by[tuple(int(x) for x in p[1:5])][(v["q"], v["s"])] = v
    return by


IA, IB = idx(A), idx(B)


def sig(v):
    return None if v is None else (v["o"], v["r"], json.dumps(v["v"], sort_keys=True, default=str))


def classify(bar):
    a, b = IA.get(bar, {}), IB.get(bar, {})
    twin = own = False
    for (q, s), vb in b.items():
        if q != "stem_direction":
            continue
        va = a.get((q, s))
        if sig(va) == sig(vb):
            continue
        du = b.get(("duration", s))
        if du and du["r"] == "owned_by_another_staff":
            twin = True
        else:
            own = True
    ev = any(sig(a.get((q, s))) != sig(b.get((q, s))) for (q, s) in set(a) | set(b) if q in ("event", "voices"))
    return ("twin-dir" if twin else "") + ("+" if twin and own else "") + ("own-dir" if own else "") + (" event/voices" if ev else "") or "none"


redA = {(r["page"], r["system"], r["staff"], r["cell"]) for r in A["red"]}
redB = {(r["page"], r["system"], r["staff"], r["cell"]) for r in B["red"]}
keep = lambda b: pages is None or b[0] in pages
print("new red bars:", collections.Counter(classify(b) for b in redB - redA if keep(b)))
print("cleared red bars:", collections.Counter(classify(b) for b in redA - redB if keep(b)))


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg"):
            o[h["rg"]].append(h)
    return o


HA, HB = hosts(A), hosts(B)


def bar_rg(rg):
    p = rg.split("/")
    return tuple(int(x) for x in p[1:5])


for kind in ("tie", "flag"):
    c = collections.Counter()
    for rg, hs in HA.items():
        if not keep(bar_rg(rg)):
            continue
        na = sum(len((h.get("sub") or {}).get(kind) or ()) for h in hs)
        nb = sum(len((h.get("sub") or {}).get(kind) or ()) for h in HB.get(rg, ()))
        if na > nb:
            c[classify(bar_rg(rg))] += na - nb
    print(kind, "lost by bar class:", dict(c))
c = collections.Counter()
for rg, hs in HB.items():
    if not keep(bar_rg(rg)):
        continue
    nb = sum(1 for h in hs if h.get("kind") == "rest")
    na = sum(1 for h in HA.get(rg, ()) if h.get("kind") == "rest")
    if nb > na:
        c[classify(bar_rg(rg))] += nb - na
print("rests gained by bar class:", dict(c))
