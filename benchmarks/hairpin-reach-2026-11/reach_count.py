"""ROADMAP 2.254: the reader as the gather calls it, OFF vs ON (`detect_hairpins(reach=...)`), on one page's master-cell-map staves and raw
page ink (no detector blanking: the shared slices no longer hold every sample page's boxes). Prints counts by width; writes the finds.

    python3 benchmarks/hairpin-reach-2026-11/reach_count.py OUTDIR brahms 19 25 ...
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_misses as P  # noqa: E402

from tools.omr import hairpin_detection as H  # noqa: E402
from tools.omr.staged import cell_map  # noqa: E402
from tools.omr.staged.gather import _system_local  # noqa: E402


def fmt(rows):
    return "%d (>=4 sp %d, 1.6-4 %d, <1.6 %d)" % (len(rows), sum(r["w_sp"] >= 4 for r in rows),
                                                  sum(1.6 <= r["w_sp"] < 4 for r in rows), sum(r["w_sp"] < 1.6 for r in rows))


def main(out, plate, pages):
    for pg in pages:
        (pws, _cells), = cell_map.load_prepared(P.C.EDITIONS[plate][0], [pg])
        ink = (pws.page.binary == 0).astype(np.uint8) * 255
        rows = P.staff_rows(pws)
        sp = {r["index"]: r["spacing"] for r in rows}
        local = _system_local(pws.staves)
        res = {}
        for arm, reach in (("off", False), ("on", True)):
            found = H.detect_hairpins(ink, rows, None, reach=reach)
            res[arm] = [{"staff": h.staff_index, "system": local[h.staff_index][0], "bbox": [h.x, h.y, h.x + h.width, h.y + h.height],
                         "w_sp": round(h.width / sp[h.staff_index], 2), "kind": h.kind} for h in found]
        (out / ("%s_p%02d_reach.json" % (plate, pg))).write_text(json.dumps(res, indent=0))
        print("%s p%d OFF %s | ON %s" % (plate, pg, fmt(res["off"]), fmt(res["on"])), flush=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), sys.argv[2], [int(v) for v in sys.argv[3:]])
