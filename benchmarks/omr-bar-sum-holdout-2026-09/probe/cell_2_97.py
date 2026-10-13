"""ROADMAP 2.97 -- print everything a saved result says about one bar.
   python3 cell_2_97.py RESULT.json page/system/staff/cell"""
import json
import sys

d = json.load(open(sys.argv[1]))
rec = d["result"]["record"]
p = sys.argv[2]
cell = "cell/" + p
sysk = "system/" + "/".join(p.split("/")[:2])
vs = rec["verdicts"]
for v in vs:
    s = v["subject"]
    if v["quantity"] == "meter" and s == sysk:
        print("METER", v["outcome"], v.get("reason"), json.dumps(v.get("value"))[:300])
    if v["quantity"] == "event" and s == cell:
        print("EVENT", json.dumps(v["value"])[:900])
    if v["quantity"] == "duration" and (s == cell or s.startswith("glyph/" + p + "/")):
        c = [(x["value"].get("beats"), x["value"].get("beam_levels"), x.get("support"))
             for x in (v.get("candidates") or []) if isinstance(x["value"], dict)]
        val = v.get("value") or {}
        print("DUR", s, v["outcome"], v.get("decider"), v.get("reason"),
              "beats", val.get("beats"), "cands", c, "ss", v.get("supersedes"))
rep = d["report"]
print([k for k in rep][:60])
