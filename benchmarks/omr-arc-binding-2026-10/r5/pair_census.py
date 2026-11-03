"""Tie pairs (union of OFF and ON tie_pair verdicts) and each head's readings in the ON gather: box centre, hole (moved or
refused + why), ink. Which reading makes the two tied heads agree? (my probe; Sean's ties are the evidence, not this)
args: OFF.record ON.record out.json"""
import sys, json, collections
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a8ed964f5bc0cc9cf")
from tools.omr.staged.record_io import load_record


def load(p):
    r = load_record(p)
    return r.get("record", r)


off, on = load(sys.argv[1]), load(sys.argv[2])
pairs = set()
for rec in (off, on):
    for v in rec["verdicts"]:
        if v["quantity"] == "tie_pair" and isinstance(v.get("value"), dict):
            a, b = v["value"].get("start"), v["value"].get("stop")
            if a and b:
                pairs.add((a, b))
del off
heads = {}
for o in on["observations"]:
    if o["quantity"] == "notehead_staff_position":
        d = o.get("detail") or {}
        heads[o["subject"]] = dict(pos=float(o["value"]), box=d.get("detector_position_float", float(o["value"])),
                                   hole=d.get("from_head_hole") or d.get("hole_steps"), moved="from_head_hole" in d,
                                   why=d.get("hole_refused"), ink=d.get("hole_ink_position"), cut="from_head_cut" in d)
    elif o["quantity"] == "glyph_box" and o["subject"] in heads:
        heads[o["subject"]]["cls"] = o["value"][0] if isinstance(o["value"], list) else None
        heads[o["subject"]]["page_box"] = (o.get("detail") or {}).get("bbox_page_px")
for o in on["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"] in heads:
        heads[o["subject"]]["cls"] = o["value"][0] if isinstance(o["value"], list) else None
        heads[o["subject"]]["page_box"] = (o.get("detail") or {}).get("bbox_page_px")
rows = []
c = collections.Counter()
for a, b in sorted(pairs):
    ha, hb = heads.get(a), heads.get(b)
    if not ha or not hb:
        c["missing_head"] += 1
        continue
    ra, rb = round(ha["box"]), round(hb["box"])
    oa, ob = round(ha["pos"]), round(hb["pos"])
    k = ("box_same" if ra == rb else "box_diff") + "/" + ("on_same" if oa == ob else "on_diff")
    c[k] += 1
    rows.append(dict(start=a, stop=b, kind=k, a=ha, b=hb))
json.dump(rows, open(sys.argv[3], "w"), default=str)
print(dict(c))
for r in rows:
    if r["kind"] != "box_same/on_same":
        print(r["kind"], r["start"], {k: r["a"].get(k) for k in ("box", "pos", "hole", "why", "ink", "cls")}, "|", r["stop"], {k: r["b"].get(k) for k in ("box", "pos", "hole", "why", "ink", "cls")})
