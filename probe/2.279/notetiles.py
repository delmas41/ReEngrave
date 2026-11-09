"""2.279: the lane report's own tile cutter, restricted to GAINED NOTES (+3 controls = unchanged notes), from the arms already in
out/lane-report/2.279n/work (--reuse). Asks one thing: what is the written value of the boxed note?

usage (repo root): PYTHONPATH=. python3 probe/2.279/notetiles.py
"""
import sys

import tools.omr.staged.lane_report as L

orig = L.pick_tiles


def pt(ac, asame, seed, n_cases=9, n_controls=3):
    ac = {p: [c for c in v if c["kind"] == "note" and c.get("side") == "gained"] for p, v in ac.items()}
    asame = {p: [c for c in v if c["kind"] == "note"] for p, v in asame.items()}
    return orig(ac, asame, seed, n_cases, n_controls)


L.pick_tiles = pt
sys.argv = ["lane_report", "--flag", "OMR_DROPPED_BLUE", "--tag", "20261104-night", "--reuse", "--out", "out/lane-report/2.279n"]
L.main()
