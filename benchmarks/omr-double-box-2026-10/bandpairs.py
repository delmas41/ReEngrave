"""2.185: make a census-format file whose 'clusters' are single PAIRS in an IoU band (for crops.py). usage: bandpairs.py EXTRACT.json PAIRS.json LO HI SAMECELL(0/1) OUT.json
Reading classes only: pairs where either box is a ledgerLine / beam / staff-like structural class are left out (those cross legitimately)."""
import json, sys
ex, pr, lo, hi, sc, out = sys.argv[1:7]; lo, hi, sc = float(lo), float(hi), int(sc)
d = json.load(open(ex)); P = json.load(open(pr))["pairs"]
bx = [b for b in d["boxes"] if b["bbox"] and b["cls"] not in ("staff", "brace")]
SK = {"ledgerLine", "beam", "stem", "arpeggiato", "tie", "slur"}
cl = []
for p in P:
    if not (lo <= p["iou"] < hi): continue
    if sc and not p["same_cell"]: continue
    a, b = bx[p["a"]], bx[p["b"]]
    if a["cls"] in SK or b["cls"] in SK: continue
    mem = [dict(i=i, subject=bx[i]["subject"], cls=bx[i]["cls"], fam="", score=bx[i]["score"], src=bx[i]["reader"], fate="", why="", bbox=bx[i]["bbox"]) for i in (p["a"], p["b"])]
    cl.append(dict(members=mem, cells=1, staffs=1, iou=p["iou"]))
json.dump(dict(clusters=cl), open(out, "w")); print(len(cl), "pairs")
