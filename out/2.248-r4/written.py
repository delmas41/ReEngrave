"""Was each r3 tile's subject WRITTEN (a host in the exported file), and what does the record's not-a-notehead verdict say?
usage: written.py  (reads the r3 run dirs read-only)"""
import json
B = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a54c2f8bd7e5bd469/out/2.248-r3/"
key = json.load(open("out/print/2.248-r3-tiles/key.json"))
recs, syms = {}, {}
for t in key:
    run = "r2" if t["group"] == "r2_in_staff" else "far2"
    k = (run, t["plate"])
    if k not in syms:
        syms[k] = json.load(open(B + "%s/work/%s.on.symbols.json" % k))["hosts"]
        r = json.load(open(B + "%s/work/%s.on.gathered.record.json" % k))
        r = r.get("record", r)
        recs[k] = {v["subject"]: (v["outcome"], v.get("value"), v["reason"]) for v in r["verdicts"]
                   if v["quantity"] == "notehead_is_not_a_notehead"}
    hit = [h for h in syms[k] if h.get("rg") == t["subject"]]
    print("tile %2d %-7s %-20s %-18s written=%s nan=%s" % (
        t["tile"], t["plate"], t["subject"], t["group"],
        [(h["kind"], h["pitch"], h["blue"]) for h in hit] or "NO", recs[k].get(t["subject"])))
