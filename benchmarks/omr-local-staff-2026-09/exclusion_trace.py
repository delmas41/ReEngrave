#!/usr/bin/env python3
"""lane-ledger-exclusion: the walk's candidates / collapse / final ladder for
one head under two arms, side by side.

    python3 exclusion_trace.py SUBJECT ARM_A ARM_B
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import accidental_census as ac  # noqa: E402
import edge_census as ec  # noqa: E402
import score_exclusion as se  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402


def main():
    ec.install()
    lg.derive_far_head_step = ac._derive
    s = sys.argv[1]
    doc = "brahms1-breitkopf" if s.startswith("glyph/1/") else "beethoven5-litolff"
    h = {x["subject"]: x for x in ec.load_heads(doc)}[s]
    for arm in sys.argv[2:]:
        pos, reason, tr = ac.read(h, record=True, **se.ARMS[arm])
        print(f"== {arm}: we {pos} ref {h['truth']} | {reason}")
        print("   clears:", [(round(c['y'], 1), c['passed']) for c in tr["clears"]])
        print("   collapse:", [([round(v, 1) for v in c['before']], [round(v, 1) for v in c['after']])
                               for c in tr["collapse"]])
        print("   final ladder:", [round(v, 1) for v in tr.get("final_ladder", [])])


if __name__ == "__main__":
    main()
