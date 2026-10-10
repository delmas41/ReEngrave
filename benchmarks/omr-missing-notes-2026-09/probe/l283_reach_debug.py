#!/usr/bin/env python3
"""l283_reach_debug: for given heads, the `Q.HEAD_STEM_REACH` row (value + detail), the head's two boxes, the detector flag boxes of
its cell, and the verdict's `flags_attached`; and `rhythm._flags_on_reach_stem`'s own answer replayed on the record's rows. Why the
reach attach did / did not fire. ROADMAP 2.83 probe.

    python3 l283_reach_debug.py --record rec.json key [key ...]
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    for key in a.keys:
        g = run.glyphs[key]
        print("==", key, "box_canon", [round(v) for v in g.box_canon], "box_page", [round(v) for v in g.box_page])
        for o in run.obs_at(key, Q.HEAD_STEM_REACH):
            d = o.get("detail") or {}
            print("  reach", o["value"], {k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()})
        v = run.standing(key, Q.DURATION, "ADJUDICATE")
        det = (v or {}).get("detail") or {}
        print("  duration", v["outcome"], v["reason"], {k: det.get(k) for k in ("flags_attached", "beam_side", "stems_attached", "beam_evidence", "beams_far_side")})
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        print("  stem_direction", sd and (sd["outcome"], sd.get("reason"), sd.get("value")))
        sp = float(run.obs_at(g.cell_key, Q.CELL_STAFF_SPACE)[-1]["value"])
        print("  space", sp)
        for k2, g2 in run.glyphs.items():
            if g2.cell_key == g.cell_key and (g2.cls or "").startswith("flag"):
                print("  flag", g2.cls, [round(v) for v in g2.box_canon])


if __name__ == "__main__":
    main()
