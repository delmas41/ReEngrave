"""2.280 r3: who says a PLAIN-written quarter-like head is not a hidden eighth? Seeded sample of READ heads written plain, stem row present, duration
decided 'head_and_marks' with NO beam/flag read at the stem (stemchain.py's class), for MY look on a sheet.
usage: silent.py HEADS.jsonl PLATE N SEED OUT.png"""
import json
import random
import subprocess
import sys

heads, plate, n, seed, out = sys.argv[1:6]
rows = [json.loads(l) for l in open(heads)]
COPY = ("owned_by_another_staff", "mark_group_duplicate")
pool = []
for r in rows:
    if not r["kept"] or r["fate"] != "written" or r.get("guess") or r.get("red") or r["n_stem"] == 0 or r["fate"] in COPY:
        continue
    dv = r["duration"] or []
    if dv[:2] != ["decided", "head_and_marks"]:
        continue
    d = r["d"] or {}
    bfs = r["bfs"] or {}
    tip = (bfs.get("tip") or {}) if isinstance(bfs, dict) else {}
    if (d.get("beams_by_stem") or 0) > 0 or (d.get("levels_certain") or 0) > 0 or (d.get("flags_attached") or 0) > 0 or tip.get("stem_beamed"):
        continue
    if (r["cands"] and len(r["cands"]) > 1) or not r["cls"].startswith("noteheadBlack"):
        continue
    pool.append(r["sub"])
random.Random(int(seed)).shuffle(pool)
print("pool", len(pool), "-> sample", n)
sel = pool[:int(n)]
open(out + ".subs", "w").write(" ".join(sel))
subprocess.run([sys.executable, "benchmarks/stems-rerun-2026-11/crops.py", "sheet", heads, plate, out] + sel)
