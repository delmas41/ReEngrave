"""A saved record -> lane_report slices (`<DIR>/<plate>/{observations,abstentions,verdicts}.jsonl`, the shape `lane_report.load_slices` reads; a
`--tag DIR` that is a directory is used as built). Usage: to_slices.py REC.json DIR PLATE"""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])
r = rec.get("record", rec)
d = os.path.join(sys.argv[2], sys.argv[3])
os.makedirs(d, exist_ok=True)
for kind in ("observations", "abstentions", "verdicts"):
    with open(os.path.join(d, kind + ".jsonl"), "w") as fh:
        for row in r.get(kind) or ():
            fh.write(json.dumps(row, default=str) + "\n")
json.dump({"from": sys.argv[1]}, open(os.path.join(d, "stamp.json"), "w"))
print(d, {k: len(r.get(k) or ()) for k in ("observations", "abstentions", "verdicts")})
