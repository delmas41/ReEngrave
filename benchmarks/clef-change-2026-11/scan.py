"""Run the 2.251 C-bar test over every staff of a page (cell-map geometry, the print raster) and list what passed / nearly passed."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.getcwd(), "work-2.251"))
sys.path.insert(0, os.getcwd())
import crops
from tools.omr.staged import clef_pagewide as CP

plate = sys.argv[1]
for pg in [int(x) for x in sys.argv[2].split(",")]:
    ink = np.asarray(crops.page_img(plate, pg).convert("L")) < 128
    d = crops.cmap(plate, pg)
    for s in sorted({t["system_index"] for t in d["staves"]}):
        staves = sorted([t for t in d["staves"] if t["system_index"] == s], key=lambda t: t["line_ys"][0])
        for sl, st in enumerate(staves):
            ly = st["line_ys"]; sp = (ly[4] - ly[0]) / 4
            for c in CP.c_bars(ink, ly, sp, st["x_start"], st["x_end"]):
                if c["passed"] or c["why"] not in ("bar_too_thin",):
                    nm = CP.name_c(c["middle_y"], c["lines_local"]) if c["passed"] else None
                    print(pg, s, sl, c["x0"], c["passed"], c["why"], c["bar_width_spaces"], c["bar_run_spaces"],
                          c.get("bowl_fill_upper"), c.get("bowl_fill_lower"), nm)
