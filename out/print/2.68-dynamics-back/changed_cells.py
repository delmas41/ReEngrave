"""ROADMAP 2.68 (Sean's deductive rule): bars whose ADJUDICATE `dynamic` verdict differs between last night's
20261009-all record (A, main 00473387) and today's small re-gather (B, main 404285f3), on the pages both hold."""
import json, sys
from tools.omr.staged import readout
a = readout.load_run(sys.argv[1]); b = readout.load_run(sys.argv[2])
pages = set(b.pages())
def cells(run):
    out = {}
    for v in run.verdicts:
        if v.get("quantity") == "dynamic" and v.get("stage", "ADJUDICATE") and v["subject"].startswith("cell/"):
            if int(v["subject"].split("/")[1]) in pages:
                out[v["subject"]] = v
    return out
ca, cb = cells(a), cells(b)
rows = []
for k in sorted(set(ca) | set(cb), key=readout._subject_sort_key):
    va = (a.standing(k, "dynamic", "ADJUDICATE") or {}); vb = (b.standing(k, "dynamic", "ADJUDICATE") or {})
    if va.get("value") != vb.get("value"):
        bb = [g.box_page for g in b.glyphs.values() if g.cell_key == k and g.family == "dynamic" and g.box_page]
        rows.append({"cell": k, "before": va.get("value"), "after": vb.get("value"), "dynamic_boxes_after": bb})
print(json.dumps(rows, indent=1))
