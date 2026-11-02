"""Cut a record file's GATHER rows to some pages (+ every document-level row) for `replay.py` (ROADMAP 2.249; streamed).

usage: slice_gather.py RECORD FIRST-LAST OUT.record.json
"""
import sys, json
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array

src, rng, dst = sys.argv[1:4]
a, b = (int(x) for x in rng.split("-"))


def page_of(subj):
    p = str(subj or "").split("/")
    return int(p[1]) if len(p) > 1 and p[1].lstrip("-").isdigit() else None


with open(dst, "w") as fh:
    fh.write('{"record":{')
    for k, kind in enumerate(("observations", "abstentions")):
        fh.write(("," if k else "") + json.dumps(kind) + ":[")
        n = 0
        for r in iter_array(src, kind):
            pg = page_of(r.get("subject"))
            if pg is None or a <= pg <= b:
                fh.write(("," if n else "") + json.dumps(r, separators=(",", ":"), default=str)); n += 1
        fh.write("]")
        print(kind, n, flush=True)
    fh.write(',"verdicts":[]}}')
