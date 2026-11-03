"""Arc boxes refused `ink_is_a_staff_line` and what the system-arc trace says about them. args: record out.json"""
import sys, json, collections
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
from tools.omr.staged.record_io import load_record
r = load_record(sys.argv[1]); r = r.get("record", r)
ref = {}
for v in r["verdicts"]:
    if v["quantity"] == "arc_is_not_an_arc" and v.get("reason") == "ink_is_a_staff_line":
        ref[v["subject"]] = dict(detail=v.get("detail"))
for o in r["observations"]:
    s = o["subject"]
    if s in ref:
        if o["quantity"] == "system_arc":
            d = o.get("detail") or {}
            ref[s]["sa"] = o["value"]
            ref[s]["cov"] = d.get("coverage")
            ref[s]["ends"] = d.get("end_heads") or d.get("ends")
            ref[s]["pieces"] = d.get("pieces")
        elif o["quantity"] == "glyph_box":
            ref[s]["box"] = (o.get("detail") or {}).get("bbox_page_px")
            ref[s]["cls"] = o["value"][0] if isinstance(o["value"], list) else None
        elif o["quantity"] == "glyph_conf":
            ref[s]["conf"] = o["value"]
for v in r["verdicts"]:
    if v["quantity"] == "tie_pair" and v["subject"] in ref:
        ref[v["subject"]]["tie_pair"] = v.get("reason")
c = collections.Counter((x.get("sa"), bool(x.get("cov") and max(x["cov"]) >= 0.5)) for x in ref.values())
print(len(ref), c.most_common())
json.dump(ref, open(sys.argv[2], "w"), default=str)
