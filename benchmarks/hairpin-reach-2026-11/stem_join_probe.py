"""ROADMAP 2.261 fix 1 probe: for every reach find (ON arm of `detect_hairpins`) on a page, how many stems are joined to its two ends.

    python3 benchmarks/hairpin-reach-2026-11/stem_join_probe.py litolff 2 3 4
"""
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_misses as P  # noqa: E402

from tools.omr import hairpin_detection as H  # noqa: E402
from tools.omr.staged import cell_map  # noqa: E402


def main(plate, pages):
    for pg in pages:
        (pws, _cells), = cell_map.load_prepared(P.C.EDITIONS[plate][0], [pg])
        ink = (pws.page.binary == 0).astype(np.uint8) * 255
        rows = P.staff_rows(pws)
        sp = {r["index"]: r["spacing"] for r in rows}
        off = H.detect_hairpins(ink, rows, None, reach=False)
        on = H.detect_hairpins(ink, rows, None, reach=True)
        offk = {(h.staff_index, h.x) for h in off}
        for h in on:
            s = sp[h.staff_index]
            j = H.stem_joins(ink, h.x, h.y, h.width, h.height, s)
            print("%s p%d staff%d x%d w%.1fsp open%.2f %s %s joins L%s R%s" % (
                plate, pg, h.staff_index, h.x, h.width / s, h.open_spaces, h.kind,
                "plain" if (h.staff_index, h.x) in offk else "reach", j[0], j[1]), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], [int(v) for v in sys.argv[2:]])
