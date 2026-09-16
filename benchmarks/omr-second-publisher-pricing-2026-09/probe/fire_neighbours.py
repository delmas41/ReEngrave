"""FOR EACH FIRE: is the SAME INK also detected by the staff it really belongs to?

⚠️ THE QUESTION THAT DECIDES WHETHER A DELETION COSTS ANYTHING. Every crop of
the Breitkopf fires shows ink that stands OUTSIDE the staff it is filed under —
a neighbouring staff's rest, notehead or time-signature digit that landed in
this cell because a measure cell is padded several staff spaces above and below.
Deleting such a reading is free IF the staff that owns the ink read it too, and
costs a symbol if it did not.

It is asked by geometry in PAGE PIXELS and nothing else: any detection of ANY
staff whose page box overlaps this one. No class is required to match, because
the whole point is that the two staves may have called the same ink different
things — which is how a whole rest becomes a notehead in the first place.

⚠️ AN OVERLAP IS NOT PROOF THE OTHER STAFF READ IT RIGHT, only that the ink is
not unread. Stated as `also_seen_by_another_staff`, never as "safe".

    python3 fire_neighbours.py --cache C --fires out/fires.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from whole_rest_reach import load, _k  # noqa: E402


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    aa = (a[2] - a[0]) * (a[3] - a[1])
    bb = (b[2] - b[0]) * (b[3] - b[1])
    return inter / max(1e-9, aa + bb - inter)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--fires", required=True)
    ap.add_argument("--iou", type=float, default=0.10)
    ap.add_argument("--json")
    a = ap.parse_args()

    _c, box, cls, rest, conf, _lines, _spacing = load(a.cache)
    fires = json.load(open(a.fires))
    if not fires:
        print("NO FIRES — nothing to check.", file=sys.stderr)
        return 2
    if not box:
        print("NO PAGE BOXES — a clean 'nothing overlaps' would be about the "
              "projection, not the page.", file=sys.stderr)
        return 2

    # index every page box by (page, staff) so a same-page, other-staff lookup
    # is cheap. ⚠️ SAME PAGE ONLY: two pages superimpose exactly in page
    # pixels, the `Q.ONSET_COLUMN` frame fault, which has already bitten one
    # probe in this repo.
    by_page = collections.defaultdict(list)
    for s, b in box.items():
        p = int(s.split("/")[1])
        by_page[p].append((s, b))

    rows, tally = [], collections.Counter()
    for f in fires:
        s = f["subject"]
        p = f["where"]["page"]
        mine_staff = _k(s, 3)
        b = box[s]
        others = []
        for s2, b2 in by_page[p]:
            if _k(s2, 3) == mine_staff or s2 == s:
                continue
            v = _iou(b, b2)
            if v >= a.iou:
                kind = ("rest:" + str(rest[s2]) if s2 in rest
                        else ("notehead:" + str(cls[s2]) if s2 in cls
                              else "other"))
                others.append({"subject": s2, "iou": round(v, 3),
                               "kind": kind, "conf": conf.get(s2)})
        others.sort(key=lambda o: -o["iou"])
        state = ("also_seen_by_another_staff" if others
                 else "seen_ONLY_here")
        tally[state] += 1
        rows.append({"subject": s, "staff_step": f["staff_step"],
                     "witness": f.get("witness"), "state": state,
                     "others": others})

    print(f"overlap threshold IoU >= {a.iou}")
    print()
    for r in rows:
        print(f"{r['subject']:<26} step {r['staff_step']:+6.2f}  {r['state']}")
        for o in r["others"][:3]:
            print(f"      IoU {o['iou']:.2f}  {o['subject']:<26} {o['kind']}")
    print()
    print("SUMMARY:", dict(tally))
    print()
    print("  `also_seen_by_another_staff`  the ink is read elsewhere too, so "
          "dropping this copy does not lose it")
    print("  `seen_ONLY_here`              this is the ONLY reading of that "
          "ink; dropping it drops the ink")
    if a.json:
        json.dump({"tally": dict(tally), "rows": rows}, open(a.json, "w"),
                  indent=1)
        print(f"\nwrote -> {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
