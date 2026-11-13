"""2306 r2: from diag_replay's two arms, per NEW red bar and per LOST tie / flag / GAINED rest: the first verdict that differs in that bar (in
adjudicate.ORDER, then by quantity name for later stages), grouped. Usage: diag_compare.py PREFIX [--pages ...]"""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
from tools.omr.staged.adjudicate import ORDER

pre = sys.argv[1]
pages = None
if "--pages" in sys.argv:
    pages = {int(x) for x in sys.argv[sys.argv.index("--pages") + 1].split(",")}
A = json.load(open(pre + ".off.json"))
B = json.load(open(pre + ".on.json"))
rank = {q: i for i, q in enumerate(ORDER)}


def bar_of(s):
    p = s.split("/")
    if p[0] in ("glyph",) and len(p) >= 5:
        return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    if p[0] == "cell" and len(p) >= 5:
        return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    return None


def index(vs):
    by = collections.defaultdict(dict)
    for v in vs:
        b = bar_of(v["s"])
        if b is not None:
            by[b][(v["q"], v["s"])] = v
    return by


IA, IB = index(A["verdicts"]), index(B["verdicts"])


def sig(v):
    if v is None:
        return None
    return (v["o"], v["r"], json.dumps(v["v"], sort_keys=True, default=str))


def diffs(bar):
    a, b = IA.get(bar, {}), IB.get(bar, {})
    out = []
    for k in set(a) | set(b):
        if sig(a.get(k)) != sig(b.get(k)):
            out.append((rank.get(k[0], 999), k[0], k[1], a.get(k), b.get(k)))
    out.sort(key=lambda t: (t[0], t[1], t[2]))
    return out


def label(d):
    if not d:
        return "no verdict differs in the bar"
    _r, q, s, a, b = d[0]
    ra = a and (a["o"], a["r"])
    rb = b and (b["o"], b["r"])
    return "%s: %s -> %s" % (q, ra, rb)


def keep(bar):
    return pages is None or bar[0] in pages


redA = {(r["page"], r["system"], r["staff"], r["cell"]) for r in A["red"]}
redB = {(r["page"], r["system"], r["staff"], r["cell"]) for r in B["red"]}
new_red = sorted(b for b in redB - redA if keep(b))
gone_red = sorted(b for b in redA - redB if keep(b))
print("red bars OFF %d ON %d; new %d, cleared %d" % (len(redA), len(redB), len(new_red), len(gone_red)))
c = collections.Counter()
for bar in new_red:
    d = diffs(bar)
    lab = label(d)
    c[lab] += 1
    qs = collections.Counter(x[1] for x in d)
    print("  NEW RED", bar, "| first:", lab, "| differing:", dict(qs.most_common(6)))
print("new red bars by first difference:")
for k, n in c.most_common():
    print("   %3d  %s" % (n, k))


def hosts_by_rg(H):
    out = collections.defaultdict(list)
    for h in H["hosts"]:
        if h.get("rg"):
            out[h["rg"]].append(h)
    return out


HA, HB = hosts_by_rg(A), hosts_by_rg(B)


def kind_lost(kind):
    lost = []
    for rg, hs in HA.items():
        if pages is not None and int(rg.split("/")[1]) not in pages:
            continue
        na = sum(len((h.get("sub") or {}).get(kind) or ()) for h in hs)
        nb = sum(len((h.get("sub") or {}).get(kind) or ()) for h in HB.get(rg, ()))
        if na > nb:
            lost.append((rg, na - nb, "note gone" if rg not in HB else "note kept"))
    return lost


def kind_gained(kind, hostkind=None):
    got = []
    for rg, hs in HB.items():
        if pages is not None and int(rg.split("/")[1]) not in pages:
            continue
        if hostkind:
            nb = sum(1 for h in hs if h.get("kind") == hostkind)
            na = sum(1 for h in HA.get(rg, ()) if h.get("kind") == hostkind)
        else:
            nb = sum(len((h.get("sub") or {}).get(kind) or ()) for h in hs)
            na = sum(len((h.get("sub") or {}).get(kind) or ()) for h in HA.get(rg, ()))
        if nb > na:
            got.append((rg, nb - na))
    return got


for kind in ("tie", "flag"):
    lost = kind_lost(kind)
    cc = collections.Counter()
    for rg, n, how in lost:
        p = rg.split("/")
        bar = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
        own = [x for x in diffs(bar) if x[2] == rg]
        lab = (how + " | own: " + label(own)) if own else (how + " | bar: " + label(diffs(bar)))
        cc[lab] += n
    print("%s lost on %d glyph keys (%d marks):" % (kind, len(lost), sum(n for _r, n, _h in lost)))
    for k, n in cc.most_common(12):
        print("   %3d  %s" % (n, k))
# rests gained: host kind rest whose rg ON has no OFF rest
gr = []
for rg, hs in HB.items():
    if pages is not None and int(rg.split("/")[1]) not in pages:
        continue
    nb = sum(1 for h in hs if h.get("kind") == "rest")
    na = sum(1 for h in HA.get(rg, ()) if h.get("kind") == "rest")
    if nb > na:
        gr.append((rg, nb - na))
# rests with no rg (filled-in) by bar
def norg_rests(H):
    c = collections.Counter()
    for h in H["hosts"]:
        if h.get("kind") == "rest" and not h.get("rg"):
            c[(h.get("part"), h.get("measure"))] += 1
    return c
nA, nB = norg_rests(A), norg_rests(B)
print("rests gained with a glyph key: %d; rests with no glyph key (filled in): OFF %d ON %d" % (sum(n for _r, n in gr), sum(nA.values()), sum(nB.values())))
cr = collections.Counter()
for rg, n in gr:
    p = rg.split("/")
    bar = (int(p[1]), int(p[2]), int(p[3]), int(p[4]))
    own = [x for x in diffs(bar) if x[2] == rg]
    cr[("own: " + label(own)) if own else ("bar: " + label(diffs(bar)))] += n
for k, n in cr.most_common(10):
    print("   %3d  %s" % (n, k))
