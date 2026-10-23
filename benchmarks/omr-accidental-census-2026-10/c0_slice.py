"""2.197 C0: cut the 20261020-night whole record to chosen pages in ONE streamed pass per array (same cut as lane_report.ensure_slices,
into our own directory so the shared lane-report slices are untouched). usage: c0_slice.py PLATE PAGES OUTDIR   (PLATE brahms|litolff, PAGES 0,1,2,3)"""
import json, sys, os, time, pathlib
sys.path.insert(0, os.getcwd())
from tools.omr.staged.judged import iter_array
from tools.omr.staged.lane_report import page_of, record_lock, record_path, STORED_QUANTITIES
plate, pages, out = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}, pathlib.Path(sys.argv[3])
d = out / plate
d.mkdir(parents=True, exist_ok=True)
rp = record_path(plate, "20261020-night")
t0 = time.time()
with record_lock():
    for kind in ("observations", "abstentions", "verdicts"):
        n = 0
        with open(d / ("%s.jsonl" % kind), "w") as fh:
            for it in iter_array(rp, kind):
                if kind == "verdicts" and it.get("quantity") not in STORED_QUANTITIES:
                    continue
                pg = page_of(it.get("subject"))
                if pg is None or pg in pages:
                    fh.write(json.dumps(it, default=str) + "\n"); n += 1
        print(plate, kind, n, "%.0fs" % (time.time() - t0), flush=True)
(d / "stamp.json").write_text(json.dumps({"pages": sorted(pages), "built_by": "2.197 c0_slice"}))
