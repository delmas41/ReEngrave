"""2.274 r3: per detector curve, whole in A and not in B (lost) / not in A and whole in B (gained).   python3 cmp3.py DIR_A DIR_B STEM [STEM ...]"""
import json
import pathlib
import sys

A, B = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
tg = tl = 0
for stem in [a for a in sys.argv[3:] if a != '-g']:
    ja = json.load(open(A / (stem + ".step1.json")))
    jb = json.load(open(B / (stem + ".step1.json")))
    ca = [c for c in ja["curves"] if not c["refused"]]
    cb = [c for c in jb["curves"] if not c["refused"]]
    lost, gained = [], []
    for x, y in zip(ca, cb):
        if x["best"] >= 0.8 and y["best"] < 0.8:
            lost.append((x["subject"], [round(v) for v in x["box"]], y.get("why_no_run"), y["best"]))
        if x["best"] < 0.8 and y["best"] >= 0.8:
            gained.append((x["subject"], [round(v) for v in x["box"]]))
    tg += len(gained)
    tl += len(lost)
    print(stem, "lost", len(lost), "gained", len(gained))
    for l in lost:
        print("  LOST", l)
    if "-g" in sys.argv:
        for g in gained:
            print("  GAINED", g)
print("TOTAL gained", tg, "lost", tl)
