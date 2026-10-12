#!/usr/bin/env python3
"""l283_tfirst_census: over the `Q.STEM_TIP_INK` rows READ AS A FLAG (value True, witness shape) at each head's TRUE tip in a record, the distribution of `t_first`
(spaces from the tip where the attached ink to the stem's right BEGINS; negative = it begins PAST the stem's end). A flag begins at the tip; ink that begins
0.3 spaces past it is something the stem runs into (Sean's tile 2: the letters of an `ff` touching a stem's end read as a flag, `t_first` -0.29).
ROADMAP 2.83 fix round probe. Read-only.

    python3 l283_tfirst_census.py rec.json [rec2.json ...] [--list-below -0.1]
"""
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def main():
    args = [a for a in sys.argv[1:]]
    cut = None
    if "--list-below" in args:
        i = args.index("--list-below")
        cut = float(args[i + 1])
        del args[i:i + 2]
    for path in args:
        run = RD.load_run(path)
        obs = {}
        for o in run.observations:
            if o["quantity"] == Q.STEM_TIP_INK and o.get("value") is True:
                d = o.get("detail") or {}
                obs[(o["subject"], d.get("stem_row_id"), d.get("end"))] = d
        vals = []
        for key, g in run.glyphs.items():
            if not (g.cls or "").startswith("notehead"):
                continue
            hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
            sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
            if not (hs and hs["outcome"] == "decided" and sd and sd["outcome"] == "decided" and sd.get("value") in ("up", "down")):
                continue
            d = obs.get((g.cell_key, hs["value"], "top" if sd["value"] == "up" else "bottom"))
            if d is None or d.get("witness") not in (None, "shape") or d.get("t_first") is None:
                continue
            vals.append((float(d["t_first"]), key, d))
        vals.sort()
        n = len(vals)
        print(path.split("/")[-1], f"flag-shaped true tips {n}")
        if n:
            q = lambda p: vals[min(n - 1, int(p * n))][0]
            print(f"   t_first: min {vals[0][0]:.2f} p1 {q(.01):.2f} p5 {q(.05):.2f} median {q(.5):.2f} p95 {q(.95):.2f} max {vals[-1][0]:.2f}")
            bins = collections.Counter(round(v[0] * 10) / 10 for v in vals if v[0] < 0.25)
            print("   below 0.25 by 0.1:", dict(sorted(bins.items())))
        if cut is not None:
            for v, key, d in vals:
                if v < cut:
                    print(f"     {key} t_first {v:.2f} out {d.get('out')} arm {d.get('arm')} covered {d.get('covered_area')}")


if __name__ == "__main__":
    main()
