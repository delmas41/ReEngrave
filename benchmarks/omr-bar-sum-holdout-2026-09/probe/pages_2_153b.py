"""ROADMAP 2.153b -- cut a night record into PER-PAGE slices in ONE streamed pass (ijson, under the record-load lock; never a
whole load). Rows whose subject names (page, system) go to that page; every other row (document, page/<p>, ...) to `common`.
Stored verdicts: duration only (the control compares the replay's OFF arm with them).
usage: pages_2_153b.py DOC OUTDIR      DOC = litolff | brahms
-> OUTDIR/<doc>/{p<NN>,common}.{observations,abstentions,verdicts}.jsonl"""
import json
import os
import sys

sys.path.insert(0, "benchmarks/gather-zoom-layers-2026-10/probe")
import rec  # noqa: E402

LIB = rec.LIB
PATHS = {"litolff": LIB + "beethoven5-litolff-mvt1-whole-20261016-night.record.json",
         "brahms": LIB + "brahms1-breitkopf-mvt1-whole-20261016-night.record.json"}
DOC, OUTDIR = sys.argv[1], sys.argv[2]
d = os.path.join(OUTDIR, DOC)
os.makedirs(d, exist_ok=True)
fh = {}


def page_of(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return "p%02d" % int(p[1])
    return "common"


n = {}
with rec.lock():
    for k in ("observations", "abstentions", "verdicts"):
        for it in rec.items(PATHS[DOC], k):
            if k == "verdicts" and it.get("quantity") != "duration":
                continue
            key = (page_of(it["subject"]), k)
            if key not in fh:
                fh[key] = open(os.path.join(d, "%s.%s.jsonl" % key), "w")
            fh[key].write(json.dumps(it, default=str) + "\n")
            n[k] = n.get(k, 0) + 1
for f in fh.values():
    f.close()
print(DOC, n, "pages", len({p for p, _ in fh}) - 1, flush=True)
