"""ROADMAP 2.311 -- the few record rows the red-bar ranking needs and the facts file does not carry (reads only).

    PYTHONPATH=. python3 benchmarks/note-loss-funnel-2026-11/redbar_extra.py REC.record.json OUT.extra.json

  staff_lines   {"p/s/i": [5 y values]}      the record's own `staff_lines` row of every staff
  dot_role      {glyph key: [outcome, value, reason]}   the record's `dot_role` verdict on every augmentation-dot box
  cell_box      {"p/s/i/c": [x0,y0,x1,y1]}   the cell rectangle the detector saw
Nothing is decided here.
"""
from __future__ import annotations

import json
import sys

from tools.omr.staged.record_io import load_record


def main(rec_path: str, out_path: str) -> None:
    r = load_record(rec_path)
    rec = r.get("record", r)
    lines, cells = {}, {}
    for o in rec["observations"]:
        q, s = o.get("quantity"), o.get("subject", "")
        v = o.get("value")
        if q == "staff_lines" and s.startswith("staff/"):
            lines[s[6:]] = json.loads(v) if isinstance(v, str) else v
        elif q == "cell_box" and s.startswith("cell/"):
            cells[s[5:]] = json.loads(v) if isinstance(v, str) else v
    roles = {}
    for v in rec["verdicts"]:
        if v.get("quantity") == "dot_role":
            roles[v["subject"]] = [v.get("outcome"), v.get("value"), v.get("reason")]
    json.dump(dict(staff_lines=lines, dot_role=roles, cell_box=cells), open(out_path, "w"))
    print(len(lines), len(roles), len(cells))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
