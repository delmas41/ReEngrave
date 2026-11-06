"""Sean's 2.271 half-arc tiles 2,4,5,9,10,12: is the box edge at a barline / cell edge? Prints the facts; crops are cut by crops_cut.py."""
import json

KEY = "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-afddbab2098760a1a/out/print/2.271-closest-key.json"
key = json.load(open(KEY))
out = []
for plate in ("litolff", "brahms"):
    d = json.load(open("results/%s.cut.json" % plate))
    rows = {r["key"]: r for r in d["rows"]}
    cur = d["curves"]
    for t in key:
        if t["plate"] != plate or t["tile"] not in (2, 4, 5, 9, 10, 12):
            continue
        r = rows.get(t["sub"])
        print("tile", t["tile"], plate, "p", t["page"], t["sub"], "start cell", t["start"].split("/")[-2], "stop cell", t["stop"].split("/")[-2],
              "sub cell", r["cell"] if r else None)
        if r:
            print("   box edge distance to its cell edge (sp): left %.2f right %.2f; box %.1f sp wide, cell %.1f sp; cut_l %s cut_r %s; partner_l %s partner_r %s" % (
                r["l_edge"], r["r_edge"], r["w_sp"], r["cellw_sp"], r["cut_l"], r["cut_r"], r["partner_l"], r["partner_r"]))
            c = cur.get(r["curve"])
            print("   curve", r["curve"], "cells", c and c["cells"], "pieces", c and c["pieces"])
            out.append(dict(tile=t["tile"], plate=plate, page=t["page"], sub=t["sub"], box=r["box"], sp=r["sp"], staff=r["staff"]))
json.dump(out, open("results/tiles_spec.json", "w"), indent=1)
