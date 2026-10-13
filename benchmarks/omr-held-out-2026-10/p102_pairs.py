"""ROADMAP 2.102 probe: which head pairs trip `_simultaneous_heads` in one cell.

    python3 benchmarks/omr-held-out-2026-10/p102_pairs.py REC cell/p/s/st/c
"""
import sys

sys.path.insert(0, "benchmarks/omr-held-out-2026-10")
sys.path.insert(0, ".")
import p102_solve as P  # noqa: E402
from tools.omr.staged.record import Kind, Q, Subject  # noqa: E402

rec, log = P.load_log(sys.argv[1])
cell = Subject.from_key(sys.argv[2])
g = log.verdict(Q.EVENT, cell)
boxes = []
for i, e in enumerate((g.value or {}).get("events", ())):
    for gl in e.get("glyphs", ()):
        rows = log.rows(Q.GLYPH_BOX, Subject(Kind.GLYPH, cell.page, cell.system,
                                             cell.staff, cell.cell, gl))
        if rows:
            v = rows[0].value
            boxes.append((round(float(v[1]) + float(v[3]) / 2.0, 1), float(v[3]), i, gl, e.get("kind"), v[0], v[2]))
boxes.sort()
for a, b in zip(boxes, boxes[1:]):
    flag = "  <-- TRIPS" if a[2] != b[2] and a[4] != "rest" and b[4] != "rest" and (b[0] - a[0]) < 0.5 * min(a[1], b[1]) else ""
    print(a, flag)
print(boxes[-1])
