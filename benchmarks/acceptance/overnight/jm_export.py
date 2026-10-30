"""Re-adjudicate a saved slice (ADJUDICATE..EXPORT, no re-gather) and list what is WRITTEN near given page boxes.
usage: jm_export.py SLICEROOT(arm dir containing litolff/) WORKDIR [ENV=VAL ...]"""
import json
import os
import pathlib
import sys

sys.path.insert(0, '.')
root, work = sys.argv[1], pathlib.Path(sys.argv[2])
for kv in sys.argv[3:]:
    k, v = kv.split("=")
    os.environ[k] = v
from tools.omr.staged import lane_report as L

out = L.run_arm("litolff", "off", [], "adjudicate", root, work, [3, 4, 13, 16])
print("control", out["control"], "red", out["red_bars"], "blue", out["blue_marks"])
PL = json.loads((pathlib.Path(__file__).parent / "jm_places.json").read_text())
for p in PL:
    b = p["box"]
    print("PLACE", p["place"], p["subject"])
    for h in out["hosts"]:
        if h.get("page") != p["page"]:
            continue
        hb = h.get("box") or h.get("bbox")
        s = json.dumps(h)
        # print hosts whose x,y fall within 60 px of the box centre
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        x, y = h.get("x"), h.get("y")
        if x is None and hb:
            x, y = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
        if x is not None and abs(x - cx) < 60 and abs(y - cy) < 60:
            print("   ", s[:300])
