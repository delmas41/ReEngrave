"""2.302: the REAL pixels of Sean's 23 judged staff starts (2.292 r1 + 2.299 r1 answers) as a test fixture: `data/real_starts.npz` + `data/real_starts.json`.
    PYTHONPATH=. python3 benchmarks/key-object-counts-flats-2026-11/make_fixtures.py PLATE EX.json PAGE:SYS:LI [...]     (run once per plate; appends)
Each case: the page raster cut to the staff's key zone (x_start-1 sp .. x_hi), the five lines (relative to the cut), spacing, x_start, x_hi (relative), the detector's
key/accidental boxes, the clef the box named, Sean's fifths, and the count `staff_run` gives OFF (the tree before 2.302) -- the control that must fail where main under-counts."""
import json
import os
import sys

import numpy as np

from tools.omr.staged import cell_map as CM
from tools.omr.staged import claims as CL
from tools.omr.staged import gather as G
from tools.omr.staged import key_object as KO
from tools.omr.staged import lane_report as LR
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare import TRUTH  # noqa: E402
from replay import _Det    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    plate, exp = sys.argv[1:3]
    wanted = [tuple(int(v) for v in a.split(":")) for a in sys.argv[3:]]
    pages = sorted({w[0] for w in wanted})
    ex = json.load(open(exp))
    G._page_box = lambda cell, det: det.pbox
    real = KO.find_object
    cap = {}

    def wrap(binary, staves, **kw):
        obj = real(binary, staves, **kw)
        for st in staves:
            cap[round(float(st["lines"][0]))] = (binary, st, obj["by_staff"][st["key"]], obj["N"])
        return obj
    KO.find_object = wrap
    pdf = LR.LIB / LR.PLATES[plate]["pdf"]
    meta = json.load(open(os.path.join(HERE, "data", "real_starts.json"))) if os.path.exists(os.path.join(HERE, "data", "real_starts.json")) else {}
    arrs = dict(np.load(os.path.join(HERE, "data", "real_starts.npz"))) if os.path.exists(os.path.join(HERE, "data", "real_starts.npz")) else {}
    for pws, cells in CM.load_prepared(pdf, pages, root=LR.CELL_MAP_ROOT):
        p = pws.page.page_index
        local = G._system_local(pws.staves)
        cap.clear()
        log = Log()
        dets = {}
        for c in cells:
            if c.measure_index != 0:
                continue
            s, li = local[c.staff_index]
            row = ex.get("%d/%d/%d" % (p, s, li)) or {"dets": [], "meter_left": None}
            dets[R.cell(p, s, li, 0).to_key()] = [_Det(d["name"], d["box"]) for d in row["dets"]]
            if row.get("meter_left") is not None:
                log.observe(R.staff(p, s, li), Q.CLAIMED_AREA, [row["meter_left"], 0.0, row["meter_left"] + 1.0, 1.0], reader=READERS.CV_KEY_OBJECT,
                            frame="cell:0", cell=0, owner=CL.OWNER_METER, unit="area", standing="READ", source="replay")
        G.gather_key_object(log, pws, cells, local, dets)
        by_line = {(local[st.staff_index]): round(float(list(st.line_ys)[0])) for st in pws.staves}
        for (wp, ws, wl) in wanted:
            if wp != p:
                continue
            binary, st, me, N = cap[by_line[(ws, wl)]]
            sp = st["spacing"]
            ly = [float(v) for v in st["lines"]]
            x0 = max(0, int(st["x_start"] - 1.0 * sp))
            x1 = min(binary.shape[1], int(st["x_hi"]) + 2)
            y0 = max(0, int(ly[0] - 3.0 * sp))
            y1 = min(binary.shape[0], int(ly[-1] + 3.0 * sp))
            key = "%s_%d_%d_%d" % (plate, wp, ws, wl)
            arrs[key] = np.ascontiguousarray(binary[y0:y1, x0:x1])
            meta[key] = {"plate": plate, "staff": "%d/%d/%d" % (wp, ws, wl), "truth_fifths": TRUTH[plate]["%d/%d/%d" % (wp, ws, wl)],
                         "lines": [v - y0 for v in ly], "spacing": sp, "x_start": st["x_start"] - x0, "x_hi": st["x_hi"] - x0, "clef": st.get("clef_measured"),
                         "boxes": [[b[0] - x0, b[1] - y0, b[2] - x0, b[3] - y0] for b in st["boxes"]], "off_count": len(me["pieces"]), "system_count": N}
    np.savez_compressed(os.path.join(HERE, "data", "real_starts.npz"), **arrs)
    json.dump(meta, open(os.path.join(HERE, "data", "real_starts.json"), "w"), indent=1)
    print(len(meta), "cases")


if __name__ == "__main__":
    main()
