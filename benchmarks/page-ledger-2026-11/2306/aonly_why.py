"""A slabs (cell reader A) the page reader does not file as a beam at the same place: which page-stroke CLAIM holds the page strokes under them."""
import sys, os, collections, json
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])
Q = M.rows_by_quantity(rec)
geo = M.cell_geometry(Q)
allp = [dict(box=M.bb(o["detail"]), role=o["value"], ord=o["detail"]["ordinal"], page=M.page_of(o["subject"]), detail=o["detail"])
        for o in Q["page_beam"] if o["value"] not in ("census", "views")]
beams = [b for b in allp if b["role"] == "beam"]
Au = M.dedup(M.a_beams(Q, geo))
aonly = [x for x in Au if not any(M.same_place(x, b) for b in beams)]
ps = [dict(kind=o["value"], box=M.bb(o["detail"]), page=M.page_of(o["subject"]), ord=o["detail"]["ordinal"]) for o in Q["page_stroke"]]
owner = {}
for o in Q["claimed_area"]:
    d = o.get("detail") or {}
    for i in d.get("page_strokes") or ():
        owner.setdefault((M.page_of(o["subject"]), int(i)), str(d.get("owner")))
role = {(b["page"], b["ord"]): b["role"] for b in allp}
c = collections.Counter()
ex = collections.defaultdict(list)
for x in aonly:
    under = [s for s in ps if s["page"] == x["page"] and s["kind"] != "barline" and M.inter_over_min(x["box"], s["box"]) >= 0.5]
    if not under:
        k = "no page stroke"
    else:
        tags = set()
        for s in under:
            k_ = (s["page"], s["ord"])
            if k_ in owner:
                tags.add("claimed:" + owner[k_])
            elif k_ in role:
                tags.add("role:" + role[k_])
            else:
                tags.add("kind:" + s["kind"])
        k = ",".join(sorted(tags))
    c[k] += 1
    ex[k].append((x["page"], [round(v) for v in x["box"]], x["cut"]))
print("A-only slabs %d:" % len(aonly))
for k, n in c.most_common():
    print("  %3d %s  e.g. %s" % (n, k, ex[k][:2]))
