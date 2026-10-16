"""ROADMAP 2.153 -- cut the rows of NAMED SYSTEMS (page,system) out of a big record, once, into a small slice file
(observations + abstentions + the record's own stored verdicts), under the record-load lock. No whole-record load
(ijson-streamed). Subjects that are not system-scoped are kept whole (they are small).
usage: slice_2_153.py RECKEY OUT.json "p,s;p,s;..."      RECKEY in rec.RECORDS (litolff | brahms | brahms_p0p3)
"""
import json
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

KEY, OUT, SYS = sys.argv[1], sys.argv[2], sys.argv[3]
keep = {tuple(int(x) for x in t.split(",")) for t in SYS.split(";") if t}


def want(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in keep
    return True


out = {"observations": [], "abstentions": [], "verdicts": []}
with rec.lock():
    for k in out:
        for it in rec.items(rec.RECORDS[KEY], k):
            if want(it["subject"]):
                out[k].append(it)
print({k: len(v) for k, v in out.items()}, flush=True)
json.dump(out, open(OUT, "w"), default=str)
