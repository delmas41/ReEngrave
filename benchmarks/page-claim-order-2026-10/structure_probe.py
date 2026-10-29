"""The one structure pass: per system left-edge rules + column classes, and detect_barlines seconds OFF vs ON. usage: structure_probe.py PDF PAGE"""
import os
import sys
import time
sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import measure_extractor as me

pws = detect_staves(render_page(sys.argv[1], int(sys.argv[2]), dpi=600))
pws.staged_page_wide = True
t = {}
for flag in ("0", "1", "0", "1"):
    os.environ["OMR_BARLINE_SYSTEM_COLUMNS"] = flag
    t0 = time.time()
    me.detect_barlines(pws)
    t.setdefault(flag, []).append(round(time.time() - t0, 2))
print("detect_barlines seconds OFF", t["0"], "ON", t["1"])
for sidx, st in sorted((getattr(pws, "system_structure", None) or {}).items()):
    from collections import Counter
    print("system", sidx, "columns", dict(Counter(c.get("span", "header/old") for c in st["columns"])))
    for r in st["left_edge"]:
        print("   ", r["kind"], "x", r["x"], "staves", len(r["staff_indices"]), "w", r["width_sp"], "drift", r["drift_sp"], "var", r["width_var_sp"])
