#!/usr/bin/env python3
"""l283_box_spaces: the detector box of given heads of a record, in STAFF SPACES (height, width), the cell's own `Q.CELL_STAFF_SPACE`.
ROADMAP 2.83 fix round probe (is a head box one head: Sean's tile 1 must stay under the cut, tile 10 over it).

    python3 l283_box_spaces.py rec.json key [key ...]
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    run = RD.load_run(sys.argv[1])
    space_of = {o["subject"]: float(o["value"]) for o in run.observations if o["quantity"] == Q.CELL_STAFF_SPACE}
    for key in sys.argv[2:]:
        g = run.glyphs.get(key)
        if g is None or not g.box_canon:
            print(key, "no box")
            continue
        sp = space_of.get(g.cell_key)
        x0, y0, x1, y1 = g.box_canon
        print(key, g.cls, f"box {x1 - x0:.0f}x{y1 - y0:.0f} px, space {sp}", f"-> height {(y1 - y0) / sp:.2f} width {(x1 - x0) / sp:.2f} spaces" if sp else "")


if __name__ == "__main__":
    main()
