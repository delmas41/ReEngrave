"""Cuts per system with the flag OFF vs ON (same raster): barline_cuts_ab.py PDF PAGES -- prints only the systems that differ."""
import os
import sys
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves
from tools.omr import measure_extractor as me

pdf, pages = sys.argv[1], [int(p) for p in sys.argv[2].split(",")]
for p in pages:
    pws = detect_staves(render_page(pdf, p, dpi=600))
    pws.staged_page_wide = True
    res = {}
    for flag in ("0", "1"):
        os.environ["OMR_BARLINE_SYSTEM_COLUMNS"] = flag
        me.detect_barlines(pws)
        res[flag] = {}
        for bl in pws.barlines:
            res[flag].setdefault(bl.system_index, []).append(bl.x)
        res[flag + "c"] = {k: v for k, v in pws.deletion_counts.items() if k.startswith("n_barline_columns")}
    for sidx in sorted(res["0"]):
        a, b = sorted(res["0"][sidx]), sorted(res["1"].get(sidx, []))
        if a != b:
            print("page", p, "system", sidx, "removed", [x for x in a if x not in b], "added", [x for x in b if x not in a])
    print("page", p, "counts", res["1c"], flush=True)
