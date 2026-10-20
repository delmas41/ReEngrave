"""2.172: for the six judged items that got worse, show the OFF/ON verdicts on the subject and the view boxes in that cell. usage: j2_why.py lit|bra SUBJECT"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pl, sub = sys.argv[1], sys.argv[2]
ARM = sys.argv[3] if len(sys.argv) > 3 else "on"
cell = "/".join(sub.split("/")[1:5])
for arm in ("off", ARM):
    d = json.loads(open(ROOT / ("rec172/%s-%s.record.json" % (pl, ARM))).read())["record"]
    print("=====", arm)
    for o in d["observations"]:
        s = o["subject"]
        if s.startswith("glyph/") and "/".join(s.split("/")[1:5]) == cell and o["quantity"] == "glyph_box":
            print("box", s, o["value"], round(o.get("score") or 0, 2), o.get("reader"))
    for v in d["verdicts"]:
        if v.get("subject") == sub:
            print("verdict", v["quantity"], v["outcome"], v.get("reason"), str(v.get("value"))[:70], v.get("decider"))
