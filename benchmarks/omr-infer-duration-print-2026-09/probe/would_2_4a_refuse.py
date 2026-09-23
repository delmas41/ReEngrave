"""§4's open question, closed: does 2.4a's shipped `clipped_fragment` refusal
fire on `glyph/2/0/9/15/5` -- one of the two inferences that override the
reader's own candidate ordering?

⚠️ THIS EVALUATES THE RULE'S TWO CONDITIONS FROM THE RECORD'S OWN GEOMETRY
rather than re-adjudicating. That is admissible ONLY because both conditions
are pure arithmetic over values this record already carries, and because
`_cell_box_page(ev)` was read and returns the raw `Q.CELL_BOX` value -- the
same number used here. It is NOT a substitute for a re-adjudication of the
whole population, which §5 still asks for.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import notehead_precision as NP  # noqa: E402
from tools.omr.staged.record_io import load_record                  # noqa: E402


def main() -> int:
    arm = sys.argv[1]
    subject = sys.argv[2] if len(sys.argv) > 2 else "glyph/2/0/9/15/5"
    cell = "cell/" + subject.split("/", 1)[1].rsplit("/", 1)[0]

    rec = load_record(arm)["record"]
    box = cellbox = space = None
    for o in rec["observations"]:
        if o["subject"] == subject and o["quantity"] == "glyph_box":
            box = o
        elif o["subject"] == cell and o["quantity"] == "cell_box":
            cellbox = o["value"]
        elif o["subject"] == cell and o["quantity"] == "cell_staff_space":
            space = float(o["value"])
    if not (box and cellbox and space):
        print("geometry missing; cannot evaluate")
        return 2

    name, _x, _y, w_c, h_c = box["value"]
    page_box = (box.get("detail") or {}).get("bbox_page_px")

    h_spaces = h_c / space
    w_spaces = w_c / space
    print(f"subject            {subject}")
    print(f"class              {name}")
    print(f"canonical w x h    {w_c} x {h_c}   (staff space {space})")
    print(f"height in spaces   {h_spaces:.3f}   max {NP.CLIPPED_NOTEHEAD_MAX_SPACES}")
    print(f"width in spaces    {w_spaces:.3f}   floor {NP.TOO_NARROW_MIN_SPACES}")
    print(f"bbox_page_px       {page_box}")
    print(f"cell_box           {cellbox}")

    short = h_spaces < NP.CLIPPED_NOTEHEAD_MAX_SPACES
    d_top = abs(page_box[1] - cellbox[1])
    d_bot = abs(page_box[3] - cellbox[3])
    touching = min(d_top, d_bot) <= NP.CELL_EDGE_TOLERANCE_PAGE_PX
    print(f"edge distance      top {d_top:.2f} px, bottom {d_bot:.2f} px, "
          f"tolerance {NP.CELL_EDGE_TOLERANCE_PAGE_PX}")
    print()
    print(f"clipped_fragment   short={short} AND touching={touching} "
          f"-> {'FIRES — 2.4a REFUSES this glyph' if short and touching else 'does not fire'}")
    narrow = (str(name).lower().startswith(NP.TOO_NARROW_CLASS_PREFIX)
              and w_spaces < NP.TOO_NARROW_MIN_SPACES)
    print(f"too_narrow         -> {'fires' if narrow else 'does not fire'}")
    return 0 if (short and touching) else 1


if __name__ == "__main__":
    raise SystemExit(main())
