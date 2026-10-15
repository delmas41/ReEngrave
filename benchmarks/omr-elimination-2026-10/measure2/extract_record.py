"""2.120 round 2 (c): ONE load of a record -> a small pickle of the detector boxes of one page. python3 extract_record.py RECORD PAGE OUT.pkl
Loaded ONLY via record_io.load_record. Per glyph: class, score, canonical + page boxes, ADJUDICATE status and, where refused, the
refusing quantity and its reason code; for litolff also the per-cell canonical->page map is derivable from box pairs."""
import sys, pickle, time
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/roadmap-start-d5bd81")
from tools.omr.staged import record_io, readout as RO
rec, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
t0 = time.time(); result = record_io.load_record(rec); print("loaded", round(time.time() - t0), flush=True)
run = RO.run_from_result(result, path=rec); print("indexed", round(time.time() - t0), "dpi", run.dpi, flush=True)
rows = []
for k, g in run.glyphs.items():
    if g.page != page: continue
    st, why = RO.adjudicate_status(run, g)
    ref = None
    for v in run.verdicts_at(k, "ADJUDICATE"):
        if "_is_not_a" in v["quantity"] and v["outcome"] == "decided" and v.get("value") is True:
            ref = (v["quantity"], v.get("reason"))
    rows.append(dict(key=k, cls=g.cls, family=g.family, score=g.score, system=g.system, staff=g.staff, cell=g.cell, index=g.index,
                     box_canon=g.box_canon, box_page=g.box_page, status=st, why=why, refusal=ref))
pickle.dump(dict(record=rec, page=page, dpi=run.dpi, pdf=run.pdf, rows=rows), open(out, "wb"))
print("wrote", out, len(rows), flush=True)
