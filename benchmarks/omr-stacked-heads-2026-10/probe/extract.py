"""2.129 step 1: record -> per-glyph facts for ONE page (noteheads + stems), read-only."""
import sys, json, time
sys.path.insert(0, ".")
from tools.omr.staged import record_io, readout as RO
rec_path, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
t0=time.time()
result = record_io.load_record(rec_path); print("loaded", round(time.time()-t0), flush=True)
run = RO.run_from_result(result, path=rec_path)
def comp(v, n=900):
    s = json.dumps(v, default=str, separators=(",", ":"))
    return s if len(s) <= n else s[:n] + "~"
glyphs = {}
for k, g in run.glyphs.items():
    if g.page != page: continue
    if not (g.cls or "").startswith("notehead"): continue
    st, why = RO.adjudicate_status(run, g)
    rows = []
    for stage, kind, r in run.rows_at(k):
        rows.append({"stage": stage, "kind": kind, "q": r.get("quantity"), "outcome": r.get("outcome"),
                     "reason": r.get("reason"), "value": comp(r.get("value"), 300), "score": r.get("score"),
                     "decider": r.get("decider") or r.get("source"), "detail": comp(r.get("detail"), 1500) if r.get("detail") else None, "id": r.get("id")})
    glyphs[k] = {"cls": g.cls, "score": g.score, "system": g.system, "staff": g.staff, "cell": g.cell, "index": g.index,
                 "box_canon": g.box_canon, "box_page": g.box_page, "adj": st, "adj_why": why, "rows": rows}
# stems per cell
stems = {}
for k, lst in run.by_subject.items():
    if not k.startswith(f"cell/{page}/"): continue
    for stage, kind, r in lst:
        if r.get("quantity") == "stem":
            stems.setdefault(k, []).append({"id": r.get("id"), "value": r.get("value")})
json.dump({"dpi": run.dpi, "pdf": run.pdf, "glyphs": glyphs, "stems": stems}, open(out, "w"), default=str)
print("wrote", len(glyphs), round(time.time()-t0), flush=True)
