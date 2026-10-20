"""2.177 helper: split a 20261018-night record into per-page jsonl slices (so later arms need not hold the 7 GB JSON).
usage: slice_record.py DOC RECORD.json OUTDIR      -> OUTDIR/DOC/pNN.{observations,abstentions}.jsonl, g.{...} (rows with no page)"""
import collections
import json
import os
import sys
import time

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

DOC, PATH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
D = os.path.join(OUT, DOC)
os.makedirs(D, exist_ok=True)
t0 = time.time()
res = load_record(PATH)
rec = res["record"] if "record" in res else res
print(DOC, "loaded %.0fs" % (time.time() - t0), list(res.keys()), flush=True)
print({k: (len(v) if hasattr(v, "__len__") else v) for k, v in rec.items()}, flush=True)


def page_of(subject):
    p = (subject or "").split("/")
    if len(p) >= 2 and p[0] in ("glyph", "cell", "staff", "system", "mark", "page", "mg", "measure") and p[1].lstrip("-").isdigit():
        return int(p[1])
    return None


for kind in ("observations", "abstentions"):
    files = {}
    cnt = collections.Counter()
    for o in rec[kind]:
        pg = page_of(o.get("subject"))
        name = "p%02d" % pg if pg is not None else "g"
        if name not in files:
            files[name] = open(os.path.join(D, "%s.%s.jsonl" % (name, kind)), "w")
        files[name].write(json.dumps(o, default=str) + "\n")
        cnt[name] += 1
    for f in files.values():
        f.close()
    print(kind, len(rec[kind]), "files", len(files), "global", cnt.get("g"), flush=True)
print("done %.0fs" % (time.time() - t0))
