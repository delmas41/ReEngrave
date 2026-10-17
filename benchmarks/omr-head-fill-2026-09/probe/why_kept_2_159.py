"""ROADMAP 2.159 round 3 -- why Sean's tiles 1 (an ff) and 4 (tremolo slashes) passed the existing not-a-note readers:
their stored notehead_is_not_a_notehead verdict (detail: tremolo_slash_signal, letter readings) and GATHER rows.
usage: why_kept_2_159.py RECORD SLICEDIR OUT.json"""
import json
import os
import pathlib
import sys

sys.path.insert(0, ".")
from tools.omr.staged.judged import iter_array  # noqa: E402

REC, SD, OUT = sys.argv[1:4]
G = ["glyph/18/1/9/6/15", "glyph/16/1/10/0/7"]
cells = {g.rsplit("/", 1)[0].replace("glyph/", "cell/") for g in G}
res = {g: {"verdicts": [], "obs": []} for g in G}
for v in iter_array(pathlib.Path(REC), "verdicts"):
    if v.get("subject") in res and v.get("quantity") != "duration":
        res[v["subject"]]["verdicts"].append({k: v.get(k) for k in ("quantity", "outcome", "value", "reason", "detail",
                                                                     "decider")})
for g in G:
    pg = int(g.split("/")[1])
    cell = g.rsplit("/", 1)[0] + "/"
    for line in open(os.path.join(SD, "brahms", "p%02d.observations.jsonl" % pg)):
        i = line.find('"subject": "')
        sub = line[i + 12:line.find('"', i + 12)]
        if sub == g or (sub.startswith(cell) and ('"glyph_box"' in line)) or sub == cell.replace("glyph/", "cell/")[:-1]:
            o = json.loads(line)
            res[g]["obs"].append({k: o.get(k) for k in ("id", "subject", "quantity", "value", "detail")})
json.dump(res, open(OUT, "w"), indent=1, default=str)
for g in G:
    print("==", g)
    for v in res[g]["verdicts"]:
        print("  V", v["quantity"], v["outcome"], v["value"], v["reason"], json.dumps(v["detail"], default=str)[:600])
    for o in res[g]["obs"]:
        if o["subject"] == g:
            print("  O", o["quantity"], json.dumps(o["value"])[:80], json.dumps(o["detail"], default=str)[:300])
    print("  cell glyph boxes:", [(o["subject"].rsplit("/", 1)[1], o["value"][0], o["value"][1:]) for o in res[g]["obs"]
                                  if o["quantity"] == "glyph_box"])
