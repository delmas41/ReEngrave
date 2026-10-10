#!/usr/bin/env python3
"""l283_head_status: for given head keys, what a record holds: whether the glyph is there, its box, its class and score, the
ADJUDICATE verdicts filed at it (quantity, outcome, reason) and `readout.adjudicate_status`. For heads that are in the base and "not
in" an arm: refused, given to another staff, or a different detector box set? ROADMAP 2.83 probe.

    python3 l283_head_status.py --record rec.json key [key ...]
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    for key in a.keys:
        g = run.glyphs.get(key)
        if g is None:
            print(key, "NOT IN THE RECORD")
            continue
        print("==", key, g.cls, "score", round(g.score or 0, 3), "box_page", [round(v) for v in g.box_page] if g.box_page else None)
        print("   status:", RD.adjudicate_status(run, g))
        for v in run.verdicts_at(key, "ADJUDICATE"):
            print("   ", v["quantity"], v["outcome"], v.get("reason"))


if __name__ == "__main__":
    main()
