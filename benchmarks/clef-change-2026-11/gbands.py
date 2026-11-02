"""Ink above / below the staff beside each C bar candidate, local lines: G clef curl and tail vs C clef (nothing)."""
import sys
import numpy as np
sys.path.insert(0, "work-2.251"); sys.path.insert(0, ".")
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
                if c["why"] == "bar_too_thin":
                    continue
                ll = c.get("lines_local") or ly
                xa, xb = int(c["x0"] - 1.0 * sp), int(c["x1"] + 1.2 * sp)
                up = ink[int(ll[0] - 2.0 * sp):int(ll[0] - 0.9 * sp), xa:xb].mean()
                lo = ink[int(ll[4] + 0.6 * sp):int(ll[4] + 1.6 * sp), xa:xb].mean()
                print(pg, s, sl, c["x0"], c["passed"], c["why"], round(float(up), 3), round(float(lo), 3))
