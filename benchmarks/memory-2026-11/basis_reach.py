"""Why a verdict's basis grows with the DOCUMENT, not the page (ROADMAP 2.249; reads a record file, streamed).

usage: basis_reach.py RECORD OUT.json

Per verdict quantity: verdicts, mean / max basis length, and how much of the basis lies on OTHER pages than the
verdict's own subject (or on document-level rows) -- by the quantity of the rows cited there. A basis that reaches
every page makes the record and ADJUDICATE's memory grow with pages x pages.
"""
import sys, json, re, mmap, collections
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array
from tools.omr.staged import record_io

src, dst = sys.argv[1:3]


def page_of(subj):
    p = str(subj or "").split("/")
    return int(p[1]) if len(p) > 1 and p[1].lstrip("-").isdigit() else None


with open(src, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as m:
    i = m.rfind(b'"' + record_io.POOL_KEY.encode() + b'":{')
    pools = {}
    if i >= 0:
        j = i + len(record_io.POOL_KEY) + 3
        pools, _ = json.JSONDecoder().raw_decode(m[j:j + (64 << 20) * 16].decode("utf-8", "ignore"))
print("pools", len(pools), flush=True)
row_page, row_q = {}, {}
for kind in ("observations", "abstentions", "verdicts"):
    for r in iter_array(src, kind):
        row_page[r["id"]] = page_of(r.get("subject")); row_q[r["id"]] = r.get("quantity")
print("rows", len(row_page), flush=True)
Q = collections.defaultdict(lambda: {"n": 0, "entries": 0, "max": 0, "other_page": 0, "doc": 0,
                                     "other_by_q": collections.Counter()})
for v in iter_array(src, "verdicts"):
    b = v.get("basis") or []
    if isinstance(b, dict):
        b = record_io._resolve(b, pools)
    q = Q[v.get("quantity")]; pg = page_of(v.get("subject"))
    q["n"] += 1; q["entries"] += len(b); q["max"] = max(q["max"], len(b))
    for rid in b:
        rp = row_page.get(rid)
        if rp is None:
            q["doc"] += 1
        elif pg is not None and rp != pg:
            q["other_page"] += 1
            q["other_by_q"][row_q.get(rid)] += 1
out = {}
for k, q in sorted(Q.items(), key=lambda kv: -kv[1]["entries"]):
    out[k] = {"verdicts": q["n"], "basis_entries": q["entries"], "mean": round(q["entries"] / max(q["n"], 1)),
              "max": q["max"], "on_other_pages": q["other_page"], "document_level": q["doc"],
              "other_pages_by_quantity": dict(q["other_by_q"].most_common(6))}
json.dump(out, open(dst, "w"), indent=1)
for k, v in list(out.items())[:25]:
    print(k, {x: v[x] for x in ("verdicts", "basis_entries", "mean", "max", "on_other_pages", "document_level")},
          v["other_pages_by_quantity"])
