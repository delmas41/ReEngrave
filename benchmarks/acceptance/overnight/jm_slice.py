"""Cut pages 3,4 (+ every document-level row) out of a Litolff night record, ALL verdict quantities, one streamed
pass per array. usage: jm_slice.py RECORD OUTDIR"""
import json
import pathlib
import sys

sys.path.insert(0, '.')
from tools.omr.staged.judged import iter_array
from tools.omr.staged.lane_report import page_of

rec, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
keep = {3, 4, 13, 16}
for kind in ("observations", "abstentions", "verdicts"):
    n = 0
    with open(out / ("%s.jsonl" % kind), "w") as fh:
        for it in iter_array(rec, kind):
            pg = page_of(it.get("subject"))
            if pg is None or pg in keep:
                fh.write(json.dumps(it, default=str) + "\n")
                n += 1
    print(kind, n, flush=True)
(out / "stamp.json").write_text(json.dumps({"pages": sorted(keep), "src": str(rec)}))
