"""Lost ties and lost rests (OFF wrote, ON does not) by the first differing verdict -- on the glyph itself, else on its tie partner's bar / its bar,
with whether the bar's voices / events changed. Usage: diag_lost.py PREFIX [--pages ...]"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
pre = sys.argv[1]
pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")} if "--pages" in sys.argv else None
from tools.omr.staged.adjudicate import ORDER
rank = {q: i for i, q in enumerate(ORDER)}
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
sig = lambda v: None if v is None else (v["o"], v["r"], json.dumps(v["v"], sort_keys=True, default=str))


def first(bar, only=None):
    a, b = IA.get(bar, {}), IB.get(bar, {})
    d = sorted((rank.get(q, 999), q, s, a.get((q, s)), b.get((q, s))) for (q, s) in set(a) | set(b)
               if sig(a.get((q, s))) != sig(b.get((q, s))) and (only is None or s == only))
    if not d:
        return None
    _r, q, s, x, y = d[0]
    return "%s %s->%s" % (q, x and x["r"], y and y["r"])


def voices_changed(bar):
    a, b = IA.get(bar, {}), IB.get(bar, {})
    return any(sig(a.get(k)) != sig(b.get(k)) for k in set(a) | set(b) if k[0] in ("voices", "event"))


def hosts(D):
    o = collections.defaultdict(list)
    for h in D["hosts"]:
        if h.get("rg"):
            o[h["rg"]].append(h)
    return o


HA, HB = hosts(A), hosts(B)
bar = lambda rg: tuple(int(x) for x in rg.split("/")[1:5])
for kind in ("tie", "rest"):
    c = collections.Counter()
    for rg, hs in HA.items():
        if pages and bar(rg)[0] not in pages:
            continue
        if kind == "tie":
            na = sum(len((h.get("sub") or {}).get("tie") or ()) for h in hs)
            nb = sum(len((h.get("sub") or {}).get("tie") or ()) for h in HB.get(rg, ()))
        else:
            na = sum(1 for h in hs if h.get("kind") == "rest")
            nb = sum(1 for h in HB.get(rg, ()) if h.get("kind") == "rest")
        if na <= nb:
            continue
        own = first(bar(rg), rg)
        lab = ("own: " + own) if own else ("bar: " + str(first(bar(rg))))
        lab += " | voices/events changed" if voices_changed(bar(rg)) else ""
        lab += " | glyph gone" if rg not in HB else ""
        c[lab] += na - nb
    print(kind, "lost:", sum(c.values()))
    for k, n in c.most_common():
        print("   %3d  %s" % (n, k))
