"""2.306 r19: cut the members of a real stem (every head whose decided `Q.HEAD_STEM` names it) from a gathered record, for the string-dot
control. Usage: r19_cut_chords.py REC OUT.json NAME@CELL@STEM_ROW_ID ... (cell = page/system/staff/cell)."""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
from tools.omr.staged.record_io import load_record  # noqa: E402
from tools.omr.staged.adjudicators import stem_value as SV  # noqa: E402

rec = load_record(sys.argv[1])
rec = rec.get("record", rec)
out = {}
for spec in sys.argv[3:]:
    name, cell, stem = spec.split("@")[:3]
    pre = "glyph/" + cell + "/"
    box = {o["subject"]: o["value"] for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"].startswith(pre)}
    hs = [v for v in rec["verdicts"] if v["quantity"] == "head_stem" and v["subject"].startswith(pre) and v.get("outcome") == "decided" and v.get("value") == stem]
    heads = []
    for v in hs:
        s = v["subject"]
        dur = [d for d in rec["verdicts"] if d["quantity"] == "duration" and d["subject"] == s and "shared_stem" not in (d.get("value") or {})]
        d = dur[0] if dur else None
        opts = []
        if d and d.get("outcome") == "decided":
            p = SV._parts(d["value"])
            opts = [list(p)] if p else []
        elif d and d.get("outcome") == "narrowed":
            for c in d.get("candidates") or ():
                p = SV._parts(c.get("value") or {})
                if p and list(p) not in opts:
                    opts.append(list(p))
        b = box[s]
        heads.append(dict(key=s, cls=b[0], box=list(b[1:5]), outcome=(d or {}).get("outcome", "none"), options=opts,
                          whole_class=SV._stands_on_a_stem_so_not_whole(b[0])))
    out[name] = dict(cell=cell, stem=stem, heads=heads)
    print(name, [(h["key"].split("/")[-1], h["cls"], h["outcome"], h["options"]) for h in heads])
json.dump(out, open(sys.argv[2], "w"), indent=1)
