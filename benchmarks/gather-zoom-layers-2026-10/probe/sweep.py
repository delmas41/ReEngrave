"""2.152 -- threshold sweep over a whole document: per kept head/rest glyph flag rate, and bar-level held vs other enrichment.
usage: sweep.py DOC   (needs tmp_2152/DOC.pkl and the 20261014-night coverage)"""
import json
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ctx  # noqa: E402

COV = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
doc = sys.argv[1]
D = ctx.Doc("tmp_2152/%s.pkl" % doc)
cov = json.load(open("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261014-night/compare/%s.coverage.json" % COV[doc]))
held = {(b["page"], b["system"], b["staff"], b["cell"]) for b in cov["bars_held_out_sum"]["held"]}
kept = [g for g, r in D.glyph.items() if r["kept"] and r["cat"] in ("notehead", "rest")]
feat = {}
for g in kept:
    z = D.p1z(g)
    z2 = D.p1z(g, "doc")
    s2 = {t: D.s2(g, t) for t in (1.0, 1.5, 3.0)}
    feat[g] = dict(zmax=None if z is None else max(z[0], z[1]), zdoc=None if z2 is None else max(z2[0], z2[1]),
                   vd=D.glyph[g]["vd"], a={t: (s and s["a"]) for t, s in s2.items()}, b=(s2[1.5] and s2[1.5]["b"]),
                   h=D.s1(g)["h"], fam=D.glyph[g]["fam"])
bars = defaultdict(list)
for g in kept:
    r = D.glyph[g]
    bars[(r["p"], r["s"], r["st"], r["cell"])].append(g)
H = [k for k in bars if k in held]
N = [k for k in bars if k not in held]


def rate(pred):
    gl = sum(1 for g in kept if pred(feat[g]))
    h = sum(1 for k in H if any(pred(feat[g]) for g in bars[k]))
    n = sum(1 for k in N if any(pred(feat[g]) for g in bars[k]))
    return gl, h, n


print(doc, "kept glyphs", len(kept), "held bars", len(H), "other bars", len(N))
print("fact\tglyphs flagged\tglyph%\theld bars\tother bars\tratio")


def line(name, pred):
    gl, h, n = rate(pred)
    hr, nr = h / len(H), n / len(N)
    print("%s\t%d\t%.1f%%\t%d (%.1f%%)\t%d (%.1f%%)\t%.2f" % (name, gl, 100 * gl / len(kept), h, 100 * hr, n, 100 * nr, hr / max(nr, 1e-9)))


for k in (3, 4, 5, 6, 8):
    line("P1 page z>%d" % k, lambda f, k=k: f["zmax"] is not None and f["zmax"] > k)
for k in (4, 6):
    line("P1 doc  z>%d" % k, lambda f, k=k: f["zdoc"] is not None and f["zdoc"] > k)
for v in (2.0, 3.0, 4.0, 5.0):
    line("S1v vd>%g" % v, lambda f, v=v: f["vd"] > v)
line("S1h", lambda f: f["h"])
for t in (1.0, 1.5, 3.0):
    line("S2a tol %g" % t, lambda f, t=t: bool(f["a"][t]))
line("S2b", lambda f: bool(f["b"]))
line("S1h or S2b", lambda f: bool(f["h"] or f["b"]))
c = Counter(feat[g]["fam"] for g in kept if feat[g]["zmax"] is not None and feat[g]["zmax"] > 4)
t = Counter(feat[g]["fam"] for g in kept)
print("P1 z>4 flagged by family:", {k: "%d/%d" % (v, t[k]) for k, v in c.most_common(8)})
print("no census (class too thin on the page):", sum(1 for g in kept if feat[g]["zmax"] is None), "of", len(kept))
