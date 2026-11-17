"""2.274 r3: are the twelve round-2 miss tiles whole now?   python3 tiles12_r3.py BASEDIR(hold-out pages of round 2, round-2 reader) NEWDIR
The picks are misses_r2.py's: positions in the seed-1 shuffle of the round-2 reader's uncovered kept curves over brahms-p22, brahms-p7, litolff-p12, litolff-p6."""
import json
import pathlib
import random
import sys

base, new = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
items = []
for stem in ("brahms-p22", "brahms-p7", "litolff-p12", "litolff-p6"):
    J = json.load(open(base / (stem + ".step1.json")))
    for k, c in enumerate(J["curves"]):
        if not c["refused"] and c["best"] < 0.8:
            items.append((stem, k, c))
random.Random(1).shuffle(items)
PICK = [0, 43, 64, 27, 1, 21, 23, 53, 17, 46, 68, 50]
whole = 0
for n, i in enumerate(PICK, 1):
    stem, k, c = items[i]
    Jn = json.load(open(new / (stem + ".step1.json")))
    cn = Jn["curves"][k]
    ok = cn["best"] >= 0.8
    whole += ok
    print("tile %2d %-12s curve %3d box %s before %.2f (%s) -> now %.2f %s" % (n, stem, k, [round(v) for v in c["box"]], c["best"], c["why_no_run"], cn["best"], "WHOLE" if ok else (cn.get("why_no_run") or "")))
print("whole now:", whole, "of", len(PICK))
