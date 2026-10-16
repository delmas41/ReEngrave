"""2.152 B -- held bars (bars_held_out_sum.held of the 20261014-night coverage) vs the other bars with events:
does any glyph in the bar carry a context flag, and is that MORE often true of held bars than of the rest (rule 7: a
fact equally common in held and non-held bars says nothing about why a bar was held).

usage: heldbars.py DOC OUT.json     DOC = litolff | brahms
"""
import json
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ctx  # noqa: E402

COV = {"litolff": "beethoven5-litolff", "brahms": "brahms1-breitkopf"}
BASE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/overnight-20261014-night/compare/%s.coverage.json"
doc = sys.argv[1]
D = ctx.Doc("tmp_2152/%s.pkl" % doc)
cov = json.load(open(BASE % COV[doc]))
held = {(b["page"], b["system"], b["staff"], b["cell"]): b for b in cov["bars_held_out_sum"]["held"]}
bars = defaultdict(list)
for g, r in D.glyph.items():
    if r["kept"] and r["cat"] in ("notehead", "rest"):
        bars[(r["p"], r["s"], r["st"], r["cell"])].append(g)

FACTS = ["P1p4", "F148", "S1v", "S1h", "S1n", "S2a", "S2b", "P1doc4"]


def flags(g):
    r = D.glyph[g]
    out = {}
    p = D.p1(g, 4.0)
    out["P1p4"] = bool(p and p["flag"])
    pd_ = D.p1(g, 4.0, "doc")
    out["P1doc4"] = bool(pd_ and pd_["flag"])
    out["F148"] = bool(r["cat"] == "notehead" and not (0.9 <= r["h"] <= 1.8 and 1.1 <= r["w"] <= 1.9))
    s1 = D.s1(g)
    out["S1v"], out["S1h"], out["S1n"] = s1["v"], s1["h"], s1["n"]
    s2 = D.s2(g, 1.5)
    out["S2a"] = bool(s2 and s2["a"])
    out["S2b"] = bool(s2 and s2["b"])
    return out


per_bar = {}
for k, gl in bars.items():
    fl = {f: [] for f in FACTS}
    for g in gl:
        for f, v in flags(g).items():
            if v:
                fl[f].append(g)
    per_bar[k] = dict(held=k in held, n=len(gl), fl=fl)
H = [k for k in per_bar if per_bar[k]["held"]]
N = [k for k in per_bar if not per_bar[k]["held"]]
print(doc, "bars with events", len(per_bar), "held (in this table)", len(H), "of coverage held", len(held),
      "non-held", len(N))
print("held bars of the coverage list with no kept head/rest glyph here:", len(set(held) - set(per_bar)))
tab = {}
for f in FACTS + ["S1any", "ANY"]:
    def has(k):
        fl = per_bar[k]["fl"]
        if f == "S1any":
            return bool(fl["S1v"] or fl["S1h"] or fl["S1n"])
        if f == "ANY":
            return any(fl[x] for x in ("P1p4", "S1v", "S1h", "S1n", "S2b"))
        return bool(fl[f])
    h = sum(1 for k in H if has(k))
    n = sum(1 for k in N if has(k))
    tab[f] = dict(held=h, held_n=len(H), other=n, other_n=len(N), held_rate=h / max(len(H), 1), other_rate=n / max(len(N), 1))
    print("%-7s held %4d/%d = %.3f   other %5d/%d = %.3f   ratio %.2f" % (f, h, len(H), h / max(len(H), 1), n, len(N),
          n / max(len(N), 1), (h / max(len(H), 1)) / max(n / max(len(N), 1), 1e-9)))
# held bars: by size of the shortfall? (want vs got) and by fact -- the named sample
rnd = random.Random(2152)
sampleH = rnd.sample(sorted(H), min(30, len(H)))
sampleN = rnd.sample(sorted(N), min(30, len(N)))


def brief(k):
    b = per_bar[k]
    row = dict(bar=list(k), held=b["held"], n=b["n"], flagged={f: v for f, v in b["fl"].items() if v and f != "P1doc4"})
    if b["held"]:
        hb = held[k]
        row["want_q"] = hb.get("want_quarters")
        row["got_q"] = hb.get("quarters")
        row["events"] = hb.get("events")
    return row


out = dict(doc=doc, table=tab, n_held=len(H), n_other=len(N), sample_held=[brief(k) for k in sampleH],
           sample_other=[brief(k) for k in sampleN])
sh = out["sample_held"]
print("sample 30 held: bars with any P1p4/S1/S2b flagged glyph:",
      sum(1 for r in sh if any(x in r["flagged"] for x in ("P1p4", "S1v", "S1h", "S1n", "S2b"))),
      "| sample 30 other:", sum(1 for r in out["sample_other"] if any(x in r["flagged"] for x in ("P1p4", "S1v", "S1h", "S1n", "S2b"))))
print("sample 30 held, per fact:", Counter(f for r in sh for f in r["flagged"]))
print("sample 30 other, per fact:", Counter(f for r in out["sample_other"] for f in r["flagged"]))
json.dump(out, open(sys.argv[2], "w"), indent=0)
