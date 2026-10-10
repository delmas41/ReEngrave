#!/usr/bin/env python3
"""l283_chord_mates: Sean's flagged heads that have NO CV stem and are not right (the 10 of FINDINGS 2.83): does each have a CHORD MATE
-- another head of the same cell standing in the same column (left edges within 0.5 spaces, so one stem passes them both) -- whose own
standing duration verdict is an eighth (decided level >= 1)? If so the flag is read and attached on the stem's one touching head and
the stemless mates simply never get it: the duration is shared in print, not in the record. Counts only; nothing is attached.
ROADMAP 2.83 probe.

    python3 l283_chord_mates.py --record rec.json --rows truth_rows.json [--arm base]
"""
import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def level_of(v):
    if v is None:
        return None
    if v["outcome"] == "decided":
        return (v.get("value") or {}).get("beam_levels")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--rows", required=True)
    ap.add_argument("--arm", default="base")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    rows = json.loads(Path(a.rows).read_text())
    tally = collections.Counter()
    for r in rows:
        if r["kind"] != "flag":
            continue
        key = r[a.arm + "_key"]
        if key is None:
            continue
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        if hs is not None and hs["outcome"] == "decided":
            continue                                   # has a CV stem: not this population
        if r[a.arm][0] == "right":
            continue
        g = run.glyphs[key]
        sp_rows = run.obs_at(g.cell_key, Q.CELL_STAFF_SPACE)
        sp = float(sp_rows[-1]["value"])
        mates = []
        for k2, g2 in run.glyphs.items():
            if k2 == key or g2.cell_key != g.cell_key or not (g2.cls or "").startswith("notehead") or not g2.box_canon:
                continue
            if abs(g2.box_canon[0] - g.box_canon[0]) <= 0.5 * sp and abs(g2.box_canon[2] - g.box_canon[2]) <= 0.5 * sp:
                lv = level_of(run.standing(k2, Q.DURATION, "ADJUDICATE"))
                st = run.standing(k2, Q.HEAD_STEM, "ADJUDICATE")
                mates.append((k2, lv, "stem" if st and st["outcome"] == "decided" else "no_stem"))
        has_eighth_mate = any(lv is not None and lv >= 1 and s == "stem" for _k, lv, s in mates)
        tally[("mate with a stem reads an eighth" if has_eighth_mate else "no such mate", r[a.arm][0])] += 1
        print(r["truth"], key, r[a.arm], "mates:", mates)
    print()
    for k, n in tally.most_common():
        print(n, k)


if __name__ == "__main__":
    main()
