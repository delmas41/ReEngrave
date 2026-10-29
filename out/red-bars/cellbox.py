"""write out/red-bars/slice/PLATE/observations.jsonl holding only the cell_box observations (crop.py reads it). usage: cellbox.py RECORD PLATE"""
import json, sys, pathlib
from tools.omr.staged.record_io import load_record
rec, plate = sys.argv[1:3]
res = load_record(rec)
r = res["record"] if "record" in res else res
d = pathlib.Path("out/red-bars/slice") / plate
d.mkdir(parents=True, exist_ok=True)
n = 0
with open(d / "observations.jsonl", "w") as f:
    for o in r["observations"]:
        if o.get("quantity") == "cell_box":
            f.write(json.dumps(o, default=str) + "\n"); n += 1
print(plate, n, "cell boxes")
