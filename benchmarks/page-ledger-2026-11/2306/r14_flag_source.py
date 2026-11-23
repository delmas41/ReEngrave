"""2.306 r14 tile follow-up: for given glyph keys, the duration verdict's flag evidence (every flag-ish detail key) and the FLAG glyph boxes of the
cell with their page boxes, so a crop can show whose flag ink it is. Usage: r14_flag_source.py REC.json key,key"""
import json
import sys

from tools.omr.staged.record_io import load_record

rec = load_record(sys.argv[1])["record"]
keys = sys.argv[2].split(",")
cells = {"/".join(k.replace("glyph/", "cell/").split("/")[:5]) for k in keys}
for v in rec["verdicts"]:
    if v["quantity"] == "duration" and v["subject"] in keys:
        d = v.get("detail") or {}
        print(v["subject"], v["outcome"], v.get("reason"), json.dumps(v.get("value"), default=str))
        print("   ", json.dumps({k: d[k] for k in d if "flag" in k or k in ("tip", "beams_by_stem", "stems_attached")}, default=str)[:1500])
        print("    used", [u for u in (v.get("used") or [])][:30])
ids = {}
for o in rec["observations"]:
    sub = o["subject"]
    if o["quantity"] == "glyph_box" and "/".join(sub.replace("glyph/", "cell/").split("/")[:5]) in cells:
        val = o.get("value") or []
        if val and ("flag" in str(val[0]).lower()):
            print("FLAGBOX", sub, o["id"], val[0], (o.get("detail") or {}).get("bbox_page_px"), o.get("score"))
    if o["quantity"] in ("flag", "stem_tip_ink", "stem_tip_hooks") and "/".join(sub.replace("glyph/", "cell/").split("/")[:5]) in cells:
        print(o["quantity"], sub, o["id"], json.dumps(o.get("value"), default=str)[:200], json.dumps(o.get("detail"), default=str)[:300])
