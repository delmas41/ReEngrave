"""Page beams with no A slab (the M4a 'false beam' pool) crossed with the 2.284 ledger owner of their ink (from stem_beam_census's json)."""
import sys, os, json, collections
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "benchmarks/page-ledger-2026-11")
import m4a_controls as M
from tools.omr.staged.record_io import load_record

rec_path = sys.argv[1]
rec = load_record(rec_path)
Q = M.rows_by_quantity(rec)
geo = M.cell_geometry(Q)
allp = [dict(box=M.bb(o["detail"]), role=o["value"], ord=o["detail"]["ordinal"], page=M.page_of(o["subject"]), detail=o["detail"])
        for o in Q["page_beam"] if o["value"] not in ("census", "views")]
beams = [b for b in allp if b["role"] == "beam"]
Au = M.dedup(M.a_beams(Q, geo))
ponly = [b for b in beams if not any(M.same_place(x, b) for x in Au)]
cen = json.load(open(rec_path + ".2306-census.json"))
owner_of = {}
for k, lst in cen["fam_ex"].items():
    for pg, o in lst:
        owner_of[(pg, o)] = k
c = collections.Counter(owner_of.get((b["page"], b["ord"]), "?") for b in ponly)
print("page-only beams %d by ledger owner:" % len(ponly))
for k, n in c.most_common():
    print("  %3d %s" % (n, k))
c2 = collections.Counter((b["detail"].get("head_fused"), len(b["detail"].get("stems") or ())) for b in ponly)
print("  (head_fused, n stems):", dict(c2))
json.dump([[b["page"], b["ord"], b["box"], owner_of.get((b["page"], b["ord"]))] for b in ponly], open(rec_path + ".2306-ponly.json", "w"))
