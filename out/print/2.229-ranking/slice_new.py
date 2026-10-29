"""2.229: cut a saved record to its loaded pages in the lane_report slice format (STORED verdicts only), reusing lane_report's own helpers.
usage: slice_new.py RECORD OUTDIR PLATE PAGES   (writes OUTDIR/PLATE/{observations,abstentions,verdicts}.jsonl)"""
import json, pathlib, sys, time
from tools.omr.staged import lane_report as L
from tools.omr.staged.judged import iter_array
rec, out, plate, pages = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3], {int(x) for x in sys.argv[4].split(",")}
d = out / plate
d.mkdir(parents=True, exist_ok=True)
t0 = time.time()
with L.record_lock():
    for kind in ("observations", "abstentions", "verdicts"):
        n = 0
        with open(d / ("%s.jsonl" % kind), "w") as fh:
            for it in iter_array(rec, kind):
                if kind == "verdicts" and it.get("quantity") not in L.STORED_QUANTITIES:
                    continue
                pg = L.page_of(it.get("subject"))
                if pg is None or pg in pages:
                    fh.write(json.dumps(it, default=str) + "\n"); n += 1
        print(plate, kind, n, "rows %.0fs" % (time.time() - t0), flush=True)
