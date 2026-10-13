"""ROADMAP 2.102 probe: what a cell holds.

    python3 benchmarks/omr-held-out-2026-10/p102_cell.py REC cell/p/s/st/c [more cells]
"""
import sys

sys.path.insert(0, ".")
from tools.omr.staged.record_io import load_record  # noqa: E402

doc = load_record(sys.argv[1])
rec = doc["record"] if "record" in doc else doc
cells = sys.argv[2:]


def under(sub, c):
    return sub == c or sub.startswith(c + "/")


for c in cells:
    print("=====", c)
    for o in rec["observations"]:
        if under(o["subject"], c) and o["quantity"] in (
                "tuplet_marker", "tuplet_marker_position", "glyph_box"):
            d = o.get("detail") or {}
            print(" OBS", o["subject"], o["quantity"], str(o["value"])[:40],
                  {k: d[k] for k in d if k in ("class", "is_bracket", "x0", "x1")})
    last = {}
    for v in rec["verdicts"]:
        if under(v["subject"], c) and v["quantity"] in (
                "tuplet_ratio", "duration", "tuplet_marker_is_not_a_marker"):
            last[(v["subject"], v["quantity"])] = v
    for (s, q), v in sorted(last.items()):
        print(" VRD", s, q, v["outcome"], str(v["value"])[:70], v["decider"],
              v["reason"])
