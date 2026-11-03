"""Are two staged record FILES the same record, whatever their file format? (ROADMAP 2.249 m8; reads only, streamed)

usage: same_record.py A.record.json B.record.json

A format-2 file stores an ADJUDICATE verdict's `considered` and derives its basis; a format-1 file spells every
basis. So two runs that read the same give different BYTES across the format change; this compares their CONTENT:
every observation and abstention in order, every verdict in order with pooled lists expanded and a derived basis
spelled out (format 2 marks it `basis_from`, which is set aside), the `format` key set aside, and the envelope after
the record compared byte for byte. Exit 0 = the same record; 1 = they differ (the first differences are printed).
"""
import sys, json, mmap
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array
from tools.omr.staged import record_io as R


def pools_of(path):
    with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
        i = m.rfind(b'"' + R.POOL_KEY.encode() + b'":{')
        if i < 0:
            return {}
        j = i + len(R.POOL_KEY) + 3
        size = len(m) - j
        dec = json.JSONDecoder()
        n = 1 << 24
        while True:
            try:
                obj, _ = dec.raw_decode(m[j:j + min(n, size)].decode("utf-8", "ignore"))
                return obj
            except json.JSONDecodeError:
                if n >= size:
                    raise
                n *= 4


def tail_of(path):
    with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
        i = m.rfind(b',"summary":')
        return m[i:] if i >= 0 else b""


def expanded(v, pools):
    v = dict(v)
    R._expand_verdicts([v], pools)
    return v


def graph_of(path, pools):
    rec = {"observations": [], "abstentions": [], "verdicts": []}
    g = R._RowGraph(rec)
    for kind in ("observations", "abstentions", "verdicts"):
        for r in iter_array(path, kind):
            if kind == "verdicts":
                r = expanded(r, pools)
                if r.get(R.DERIVED_KEY) == "considered":
                    g.edges[r["id"]] = tuple(r.get("considered") or ())
                    g.derived.add(r["id"])
                    continue
            g.edges[r["id"]] = tuple(r.get("basis") or ())
    return g


pa, pb = sys.argv[1:3]
bad = 0
for kind in ("observations", "abstentions"):
    n = 0
    for x, y in zip(iter_array(pa, kind), iter_array(pb, kind)):
        if x != y:
            bad += 1
            if bad <= 5:
                print("DIFF", kind, n, x.get("id"), y.get("id"))
        n += 1
    print(kind, n, "rows compared")
P = {pa: pools_of(pa), pb: pools_of(pb)}
G = {p: graph_of(p, P[p]) for p in (pa, pb)}
n = 0
ia, ib = iter_array(pa, "verdicts"), iter_array(pb, "verdicts")
for x, y in zip(ia, ib):
    x, y = expanded(x, P[pa]), expanded(y, P[pb])
    for v, p in ((x, pa), (y, pb)):
        if v.pop(R.DERIVED_KEY, None) == "considered":
            v["basis"] = sorted(G[p].closure_of_many(v.get("considered") or ()))
    if x != y:
        bad += 1
        if bad <= 5:
            k = [k for k in set(x) | set(y) if x.get(k) != y.get(k)]
            print("DIFF verdict", n, x.get("id"), y.get("id"), "fields", k)
    n += 1
left = sum(1 for _ in ia) + sum(1 for _ in ib)
print("verdicts", n, "compared;", left, "left over")
ta, tb = tail_of(pa), tail_of(pb)
print("envelope after the record identical:", ta == tb)
bad += (left > 0) + (ta != tb)
print("SAME RECORD" if not bad else "DIFFERENT (%d)" % bad)
sys.exit(1 if bad else 0)
