"""headinfo.py RECORD PAGES glyph [glyph ...]: head_ink, notehead_ink, class, duration verdict for given glyph keys"""
import json, sys
from tools.omr.staged import lane_report as L
from tools.omr.staged.record_io import load_record
rec, pages = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
gl = set(sys.argv[3:])
res = load_record(rec)
r = res["record"] if "record" in res else res
for k in ("observations", "verdicts"):
    for o in r[k]:
        if o.get("subject") in gl and o["quantity"] in ("glyph_box", "head_ink", "notehead_ink", "duration", "stem_value", "stem_direction", "notehead_is_not_a_notehead"):
            d = o.get("detail") or {}
            v = o.get("value")
            if o["quantity"] == "notehead_ink":
                v = {"net": (d.get("ink_net") or {}).get("best"), "interior": d.get("interior_white")}
            if o["quantity"] == "head_ink":
                v = (v, d.get("margin"), d.get("slit"), d.get("window"))
            print(o["subject"], o["quantity"], o.get("outcome", ""), o.get("reason", ""), json.dumps(v, default=str)[:300], json.dumps(o.get("candidates"), default=str)[:200] if o.get("candidates") else "")
