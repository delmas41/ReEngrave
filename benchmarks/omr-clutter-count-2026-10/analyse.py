"""Group the rows by Sean's answer vs the record; clutter rates; Fisher exact; label-shuffle control."""
import json, math, random, sys, pathlib
from collections import Counter, defaultdict
D = pathlib.Path(__file__).parent
rows = []
for f in sorted(D.glob("rows-*.json")):
    d = json.load(open(f))
    for r in d["rows"]:
        r["doc"] = d["doc"]; rows.append(r)
# one mark judged twice counts once (last item name wins)
seen = {}
for r in rows: seen[(r["doc"], tuple(r["subjects"]))] = r
rows = list(seen.values())
for r in rows:
    r["grp"] = {"right": "RIGHT", "wrong": "WRONG", "narrowed": "UNDECIDED", "abstained": "UNDECIDED"}.get(r["status"])
rows = [r for r in rows if r["grp"]]
for r in rows:   # READ neighbours other than arcs (a tie/slur is laid over its notes by construction)
    for rn in ("touch", "near"):
        r[rn + "_read_noarc"] = sum(v for k, v in r[rn + "_kinds"].items() if k.endswith("+READ") and not k.startswith("arc"))

def lf(n):  return math.lgamma(n + 1)
def fisher(a, b, c, d):   # two-sided
    n = a + b + c + d; r1, r2, c1 = a + b, c + d, a + c
    def p(x): return math.exp(lf(r1)+lf(r2)+lf(c1)+lf(n-c1)-lf(n)-lf(x)-lf(r1-x)-lf(c1-x)-lf(r2-c1+x))
    p0 = p(a); return sum(p(x) for x in range(max(0, c1-r2), min(r1, c1)+1) if p(x) <= p0*(1+1e-9))
def rate(rs, key): 
    n = len(rs); k = sum(1 for r in rs if r[key] > 0); return k, n
def wil(k, n):
    if not n: return (0, 0)
    z = 1.96; p = k/n; den = 1+z*z/n; c = (p+z*z/(2*n))/den; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return (round(c-h, 2), round(c+h, 2))
out = []
def table(name, rs):
    for key, lab in (("touch_read_noarc", "READ non-arc neighbour touching"), ("near_read_noarc", "READ non-arc neighbour near (<=1sp)"), ("touch_read", "READ neighbour touching (<=0.25sp)"), ("near_read", "READ neighbour near (<=1sp)"),
                     ("touch_any", "any non-part neighbour touching"), ("near_any", "any non-part neighbour near")):
        W = [r for r in rs if r["grp"] == "WRONG"]; R = [r for r in rs if r["grp"] == "RIGHT"]; U = [r for r in rs if r["grp"] == "UNDECIDED"]
        kw, nw = rate(W, key); kr, nr = rate(R, key); ku, nu = rate(U, key)
        if nw == 0 or nr == 0: continue
        p = fisher(kw, nw-kw, kr, nr-kr)
        # shuffle control: permute WRONG/RIGHT labels among W+R, diff of rates
        lab_pool = [1 if r[key] > 0 else 0 for r in W+R]; obs = kw/nw - kr/nr; rng = random.Random(7); ds = []
        for _ in range(5000):
            rng.shuffle(lab_pool); a = lab_pool[:nw]; b = lab_pool[nw:]; ds.append(sum(a)/nw - sum(b)/nr)
        perm_p = sum(1 for x in ds if abs(x) >= abs(obs)-1e-12)/len(ds)
        out.append(f"{name:14s} {lab:36s} WRONG {kw}/{nw} {wil(kw,nw)}  RIGHT {kr}/{nr} {wil(kr,nr)}  UNDECIDED {ku}/{nu}  diff {obs:+.2f}  Fisher p={p:.3f}  shuffle: mean|diff|={sum(abs(x) for x in ds)/len(ds):.2f} perm p={perm_p:.3f}")
table("ALL", rows)
for dk in ("litolff", "brahms"): table(dk, [r for r in rows if r["doc"] == dk])
# per symbol kind (subject category) and per question
kinds = defaultdict(list)
for r in rows: kinds[(r["kind"], r["akind"])].append(r)
out.append("\nper (subject kind, answer kind): n WRONG/RIGHT/UNDECIDED, touch_read, near_read clutter counts")
for k, rs in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
    c = Counter(r["grp"] for r in rs)
    def s(g, key): 
        sub = [r for r in rs if r["grp"] == g]; return f"{sum(1 for r in sub if r[key]>0)}/{len(sub)}"
    out.append(f"  {k[0]:10s}/{k[1]:15s} n={len(rs):3d} | touch_read W {s('WRONG','touch_read')} R {s('RIGHT','touch_read')} U {s('UNDECIDED','touch_read')} | near_read W {s('WRONG','near_read')} R {s('RIGHT','near_read')} U {s('UNDECIDED','near_read')}")
out.append("\nWRONG rows (for the example read):")
for r in rows:
    if r["grp"] == "WRONG":
        out.append(f"  {r['doc']} {r['item']} {r['tile']} {r['subjects']} sean={r['answer']!r} :: {r['note']} | touch {r['touch_read']}/{r['touch_any']} near {r['near_read']}/{r['near_any']} {r['near_kinds']}")
# population + sanity
for f in sorted(D.glob("pop-*.json")):
    d = json.load(open(f)); P = d["population"]; C = d["chord_sanity"]
    rd = [p for p in P if p["read_head"]]
    out.append(f"\n{f.name}: population of {len(P)} sampled noteheads ({len(rd)} READ): touch_read {sum(p['touch_read']>0 for p in P)/len(P):.2f}, near_read {sum(p['near_read']>0 for p in P)/len(P):.2f}, near_any {sum(p['near_any']>0 for p in P)/len(P):.2f}")
    present = [c for c in C if c["mates_read"] > 0]
    out.append(f"  sanity PRESENT: {len(present)} chord heads with a READ mate -> neighbour code sees a READ neighbour (near) in {sum(c['near_read']>0 for c in present)}/{len(present)}")
    absent = [p for p in P if p["near_any"] == 0]
    out.append(f"  sanity ABSENT: {len(absent)} isolated sampled heads (no non-part glyph within 1sp) -> near_read>0 in {sum(p['near_read']>0 for p in absent)} (must be 0)")
print("\n".join(out)); open(D/"analysis.txt", "w").write("\n".join(out)+"\n")
