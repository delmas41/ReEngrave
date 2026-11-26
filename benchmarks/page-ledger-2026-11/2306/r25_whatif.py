"""What-if: give a head its head ink (the 2.290 oval flag) and/or add a contact between the head's ink and a stroke, and re-read the page offline.
Usage: whatif.py DUMPDIR plate page subject [ink] [touch=STROKE]"""
import os, pickle, sys
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
dd, plate, page, subj = sys.argv[1:5]
D = pickle.load(open(f"{dd}/{plate}/p{page}.pkl", "rb"))
h = next(h for h in D["heads"] if subj in h["members"])
base = PS.read(D["heads"], D["verticals"], D["held"], crossers=D["crossers"], strokes=D["strokes"])["heads"]
for a in sys.argv[5:]:
    if a == "ink":
        h["ink"] = True
    elif a.startswith("touch="):
        o = int(a.split("=")[1])
        hink = PS.head_ink(D["heads"], D["strokes"], D["held"])
        s = sorted(hink.get(h["id"]) or ())[0]
        D["strokes"][o]["touches"] = list(D["strokes"][o]["touches"]) + [(s, 1.0)]
        D["strokes"][s]["touches"] = list(D["strokes"][s]["touches"]) + [(o, 1.0)]
new = PS.read(D["heads"], D["verticals"], D["held"], crossers=D["crossers"], strokes=D["strokes"])["heads"]
r0, r1 = base[h["id"]], new[h["id"]]
print(subj, "before", r0["state"], r0["how"], r0.get("why"), r0.get("direction"), r0.get("voices"))
print(subj, "after ", r1["state"], r1["how"], r1.get("why"), r1.get("direction"), r1.get("voices"))
ch = [(k["members"][0], base[k["id"]]["how"], new[k["id"]]["how"]) for k in D["heads"] if k["id"] != h["id"] and
      (base[k["id"]]["state"], base[k["id"]].get("stroke"), base[k["id"]]["how"]) != (new[k["id"]]["state"], new[k["id"]].get("stroke"), new[k["id"]]["how"])]
print("other heads changed:", ch)
