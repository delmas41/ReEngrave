"""Cut a record file's GATHER rows to some pages (+ every document-level row) for `replay.py` (ROADMAP 2.249; streamed).

usage: slice_gather.py RECORD FIRST-LAST OUT.record.json [FIRST-LAST OUT.record.json ...]   (one pass, many slices)
"""
import sys, json
sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array

src = sys.argv[1]
outs = []
for i in range(2, len(sys.argv), 2):
    a, b = (int(x) for x in sys.argv[i].split("-"))
    outs.append([a, b, open(sys.argv[i + 1], "w"), 0])


def page_of(subj):
    p = str(subj or "").split("/")
    return int(p[1]) if len(p) > 1 and p[1].lstrip("-").isdigit() else None


for o in outs:
    o[2].write('{"record":{')
for k, kind in enumerate(("observations", "abstentions")):
    for o in outs:
        o[2].write(("," if k else "") + json.dumps(kind) + ":["); o[3] = 0
    for r in iter_array(src, kind):
        pg = page_of(r.get("subject"))
        line = None
        for o in outs:
            if pg is None or o[0] <= pg <= o[1]:
                line = line or json.dumps(r, separators=(",", ":"), default=str)
                o[2].write(("," if o[3] else "") + line); o[3] += 1
    for o in outs:
        o[2].write("]")
        print(kind, o[0], o[1], o[3], flush=True)
for o in outs:
    o[2].write(',"verdicts":[]}}'); o[2].close()
