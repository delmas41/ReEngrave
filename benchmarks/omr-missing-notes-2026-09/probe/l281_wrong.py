#!/usr/bin/env python3
"""l281_wrong: the page-0 members the candidate rule gets WRONG, and what the refused stroke at their
tip looks like (thickness against the 2.74 cut, bow, stems at its ends), beside the members it gets right.

    python3 l281_wrong.py --ext DIR --tag bquick --scored scored.json
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_population import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--scored", required=True)
    a = ap.parse_args()
    d, pop, _n, _sc = build(a.ext, a.tag)
    by = {m["key"]: m for m in pop}
    rows = json.loads(Path(a.scored).read_text())
    j = [r for r in rows if r["judge"] in ("right", "wrong_beam", "wrong_fill")]
    print("judge x strokes_at_tip (count) x refusal reasons")
    for r in j:
        m = by[r["key"]]
        sts = (m["at_tip_d"] or {}).get("strokes_at_tip") or []
        ink = [(s["reader"], (s["ink"] or {}).get("thickness_ratio"), (s["ink"] or {}).get("sagitta"),
                (s["ink"] or {}).get("end_stems")) for s in sts]
        print(f"{r['judge']:10s} {r['key']:18s} tip={r['tip']:15s} L{r.get('truth_levels')} "
              f"dots {m['dots']}/{r.get('truth_dots')} why={m['ink_why']} neigh={m['neigh']} arc={m['arc']} "
              f"far={m['far']} at_tip={ink}")
    print()
    print("thickness_ratio of strokes at the tip, by verdict (2.74's cut is 1.75):")
    for jd in ("right", "wrong_beam"):
        xs = []
        for r in j:
            if r["judge"] != jd:
                continue
            for s in ((by[r["key"]]["at_tip_d"] or {}).get("strokes_at_tip") or []):
                t = (s["ink"] or {}).get("thickness_ratio")
                if t is not None:
                    xs.append(round(t, 2))
        xs.sort()
        print(f"  {jd}: n={len(xs)} {xs}")


if __name__ == "__main__":
    main()
