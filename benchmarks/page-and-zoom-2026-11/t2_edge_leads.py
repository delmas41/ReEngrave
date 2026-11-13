"""ROADMAP 2.307 T2 -- 20 seeded "only cells, at a barline" boxes (cells find them within 1 sp of a cell's left/right edge, the row does
not), as a leads file for `t2_crops.py` (measure only; never called right or wrong).

    python3 benchmarks/page-and-zoom-2026-11/t2_edge_leads.py WORK_DIR OUT_LEADS.json
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_sys.path.insert(0, _os.path.dirname(__file__))

import glob
import json
import os
import random
import sys

from t2_edges import FAMS, where  # noqa: E402
from t2_score import fam_boxes, iou, merged  # noqa: E402


def main():
    work, outp = sys.argv[1], sys.argv[2]
    pool = []
    for f in sorted(glob.glob(os.path.join(work, "*.p*.json"))):
        d = json.load(open(f))
        sp = sorted(s["sp"] for s in d["staves"].values())[len(d["staves"]) // 2]
        cells = [it["bbox"] for it in d["ways"]["cells"]["items"]]
        cw = fam_boxes(merged(d["ways"]["cells"]["items"]))
        rw = fam_boxes(merged(d["ways"]["row"]["items"]))
        for fam in FAMS:
            for c in cw.get(fam, []):
                if not any(iou(b[2:], c[2:]) >= 0.3 for b in rw.get(fam, [])) and where(c, cells, sp).startswith("x-edge"):
                    pool.append(dict(page="%s/%d" % (d["plate"], d["page"]), family=fam, cls=c[0], conf=c[1], box=c[2:]))
    rng = random.Random(2307)
    json.dump({"cells_edge": rng.sample(pool, min(20, len(pool)))}, open(outp, "w"), indent=1)
    print(len(pool), "in the pool")


if __name__ == "__main__":
    main()
