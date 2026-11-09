"""2.279 r4: why does the partial-bar planner move a READ event into the gap? Runs ONE arm on one page and prints the planner's inputs
and answer for each bar holding a named glyph.

usage (repo root): PYTHONPATH=. python3 probe/2.279r3/planner_debug.py PLATE ARM PAGE GLYPH_KEY [WORKDIR]
"""
import pathlib
import sys
import tempfile

import tools.omr.staged.lane_report as L
from tools.omr.staged import export as E

plate, arm, page, key = sys.argv[1:5]
work = pathlib.Path(sys.argv[5]) if len(sys.argv) > 5 else pathlib.Path(tempfile.mkdtemp())
orig = E._partial_bar_plan


def spy(events, streams, divisions, meter, unplaced):
    r = orig(events, streams, divisions, meter, unplaced)
    gl = [h.get("glyph") for ev in events for h in (ev.get("noteheads") or ())]
    if key in gl:
        print("PLAN events", [(ev.get("x_position"), [(h.get("glyph"), h.get("duration_beats"), bool(h.get("guess"))) for h in ev.get("noteheads") or ()]) for ev in events])
        print("     unplaced", [(u["sub"], u["reason"], round(u["x"], 1)) for u in unplaced])
        print("     ok", r.get("ok"), r.get("why"), "written", [(e.get("x_position")) for e in r.get("written", [])])
    return r


E._partial_bar_plan = spy
L.run_arm(plate, arm, [("OMR_VALUE_OPEN_WRITTEN", "0", "1")], "adjudicate", "20261104-night", work, [int(page)])
