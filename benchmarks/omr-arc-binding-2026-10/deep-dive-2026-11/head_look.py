"""Where is a head the arc names, and what did the exporter write near it? (measure only) python3 head_look.py PLATE ARM HEAD [HEAD ...]"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import written as W

plate, arm = sys.argv[1], sys.argv[2]
D = pathlib.Path("scratch/dd")
dump = json.load(open(D / ("%s.%s.arcs.json" % (plate, arm))))
wr = W.parse((D / ("%s.%s.musicxml" % (plate, arm))).read_text())
heads = {h["subject"]: h for h in dump["heads"]}
vs = {}
for v in dump["verdicts"]:
    vs.setdefault(v["subject"], {})[v["quantity"]] = v
for k in sys.argv[3:]:
    h = heads.get(k)
    print("==", k, "box", h and [round(x) for x in h["box"]], "written" if k in wr["notes"] else "NOT written",
          {q: (v["outcome"], v["value"], v["reason"]) for q, v in vs.get(k, {}).items()})
    if not h:
        continue
    b = h["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    w = b[2] - b[0]
    for rg in wr["notes"]:
        hb = heads.get(rg)
        if hb and abs((hb["box"][0] + hb["box"][2]) / 2 - cx) < 2 * w and abs((hb["box"][1] + hb["box"][3]) / 2 - cy) < 2 * w:
            print("   near written:", rg, [round(x) for x in hb["box"]], wr["notes"][rg], {q: (v["outcome"], v["value"], v["reason"]) for q, v in vs.get(rg, {}).items()})
    for kk, hh in heads.items():
        if kk != k and abs((hh["box"][0] + hh["box"][2]) / 2 - cx) < 1.2 * w and abs((hh["box"][1] + hh["box"][3]) / 2 - cy) < 1.2 * w:
            print("   near box (any):", kk, [round(x) for x in hh["box"]], "written" if kk in wr["notes"] else "NOT written",
                  {q: (v["outcome"], v["value"], v["reason"]) for q, v in vs.get(kk, {}).items()})
