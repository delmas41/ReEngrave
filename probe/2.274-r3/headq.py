"""python3 headq.py X Y [R=60]: glyph boxes near a page point, whether the ON/OFF file writes them, and their verdicts"""
import sys
from load import *  # noqa

x, y = float(sys.argv[1]), float(sys.argv[2])
R = float(sys.argv[3]) if len(sys.argv) > 3 else 60
rec = record("on")
w = {a: xml_notes(a) for a in ("off", "on")}
ver = {}
for v in rec["verdicts"]:
    ver.setdefault(v["subject"], []).append(v)
for o in rec["observations"]:
    if o["quantity"] == "glyph_box" and o["subject"].startswith("glyph/0/"):
        b = o["detail"]["bbox_page_px"]
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        if abs(cx - x) <= R and abs(cy - y) <= R:
            print(o["subject"], o["detail"].get("category"), o["value"], [round(t) for t in b], "written OFF/ON", o["subject"] in w["off"], o["subject"] in w["on"])
            for v in ver.get(o["subject"], []):
                if v["quantity"] in ("notehead_is_not_a_notehead", "glyph_owner", "head_stem", "pitch", "duration", "unison_voices", "notehead_is_a_whole_rest"):
                    print("     ", v["quantity"], str(v["value"])[:60], str(v.get("detail"))[:200])
