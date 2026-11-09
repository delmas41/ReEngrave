"""2.274 r2: one line per page of a measure output dir: runs / witnessed / NEW / kept / whole / whole after seed, and pooled coverage.   python3 sumr2.py DIR [stem ...]"""
import json
import pathlib
import sys

wd = pathlib.Path(sys.argv[1])
names = sys.argv[2:] or sorted(p.name.replace(".step1.json", "") for p in wd.glob("*.step1.json"))
tk = tw = ts = nr = nn = tu = 0
for n in names:
    s = json.load(open(wd / (n + ".step1.json")))["summary"]
    print("%-12s runs %3d witnessed %3d NEW %3d | kept %3d whole %3d (%.1f%%) after seed %3d | union %3d" % (
        n, s["runs"], s["runs_witnessed"], s["runs_new"], s["curves_kept"], s["whole"], 100.0 * s["whole"] / max(1, s["curves_kept"]), s["whole_after_seed"], s.get("whole_union", 0)))
    tk += s["curves_kept"]
    tw += s["whole"]
    ts += s["whole_after_seed"]
    tu += s.get("whole_union", 0)
    nr += s["runs"]
    nn += s["runs_new"]
print("POOLED runs %d NEW %d | kept %d whole %d (%.1f%%) after seed %d (%.1f%%) | union %d (%.1f%%)" % (nr, nn, tk, tw, 100.0 * tw / max(1, tk), ts, 100.0 * ts / max(1, tk), tu, 100.0 * tu / max(1, tk)))
