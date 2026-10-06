"""lane-local-staff-lines (Sean: "if the crop can't obviously tell where the staff is then the cell is being cut poorly"):
for every fit the OLD read flagged implausible, is the cause that the known staff's lines (the window centres, from staff
detection / the cell frame) sit off the ink -- so the +-0.5 space windows cut the real staff off? Measured: the median
offset of the NEW (comb-fitted) lines from the global lines, in that staff's spaces.
  python3 local_lines_crop_cause.py <audit.json> [...]"""
import collections, json, statistics, sys

for p in sys.argv[1:]:
    d = json.load(open(p))
    c = collections.Counter()
    off = []
    for r in d["rows"]:
        for k, v in r["cand"].items():
            if not v["old_flag"]:
                continue
            gl = v["gl"]
            sp = (max(gl) - min(gl)) / 4.0
            c["old_flagged"] += 1
            if v["new"] is None:
                c["new_not_fitted(ink itself broken)"] += 1
                continue
            s = statistics.median(a - b for a, b in zip(v["new"], gl)) / sp
            off.append(abs(s))
            c["global_off_ink_ge_0.4sp(windows cut the staff)"] += (abs(s) >= 0.4)
            c["global_off_ink_0.2_0.4sp"] += (0.2 <= abs(s) < 0.4)
            c["global_off_ink_lt_0.2sp(ink: merged bars/smudge)"] += (abs(s) < 0.2)
    print("==", d["doc"], dict(c), "median |offset| sp", round(statistics.median(off), 3) if off else None)
    allfits = [(v, ) for r in d["rows"] for v in r["cand"].values()]
    big = 0
    for r in d["rows"]:
        for v in r["cand"].values():
            gl = v["gl"]; sp = (max(gl) - min(gl)) / 4.0
            if v["new"] is not None and abs(statistics.median(a - b for a, b in zip(v["new"], gl))) / sp >= 0.4:
                big += 1
    print("   ALL fits with global lines >=0.4 sp off the ink:", big, "of", len(allfits))
