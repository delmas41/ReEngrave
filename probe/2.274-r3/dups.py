import json
C = json.load(open("census2.json"))
n = 0
for i, a in enumerate(C):
    for b in C[i + 1:]:
        if a["staff"] != b["staff"]:
            continue
        if abs(a["x0"] - b["x0"]) <= 40 and abs(a["x1"] - b["x1"]) <= 40:
            iy = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
            print("P%d(%s y%d-%d) vs P%d(%s y%d-%d) x %d-%d / %d-%d  yoverlap %d  file_on %s/%s" % (a["n"], a["kind"], a["y0"], a["y1"], b["n"], b["kind"], b["y0"], b["y1"], a["x0"], a["x1"], b["x0"], b["x1"], iy, a["file_on"], b["file_on"]))
            n += 1
print(n)
