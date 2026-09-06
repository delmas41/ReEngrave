"""Is DETECTION CONFIDENCE evidence about which staff OWNS a contested glyph?

`_dedupe_cross_staff_detections` holds both copies' confidences at the moment it
decides and reads neither; the standing suggestion is to add a confidence
tie-break under rank 0 (distance). This asks whether that would be evidence or
noise, and it does so WITHOUT ground truth, using an internal gold standard the
pipeline already trusts:

    the LADDER tier (rank 2) is the strongest evidence in the function -- an
    unbroken run of ledger lines physically joining a glyph to a staff. If
    confidence carried ownership information, it would agree with the ladder
    more often than chance. Measure P(winner conf > loser conf) on ladder-
    decided pairs.

A cross-staff duplicate is TWO CROPS OF THE SAME INK, so the prior is that
confidence answers "is this a notehead", not "whose notehead is it". This tests
that prior instead of assuming it.

Then, for the population a tie-break would actually act on (rank 0), it reports
how often confidence would OVERTURN distance -- reach, not accuracy.

    python3 analyse_contests.py            # over out/contests/*.contests.json
"""
from __future__ import annotations

import collections
import glob
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CONTESTS = os.path.join(HERE, "..", "out", "contests", "*.contests.json")


def wilson(k, n, z=1.96):
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def main():
    paths = sorted(glob.glob(CONTESTS))
    tiers = collections.Counter()
    cat = collections.Counter()
    agree = collections.Counter()          # (tier) -> winner conf > loser conf
    ties = collections.Counter()
    margins = collections.defaultdict(list)
    per_row = collections.defaultdict(collections.Counter)
    rows = 0
    for path in paths:
        doc = json.load(open(path))
        rows += 1
        row = doc["row_id"]
        for page in doc["pages"]:
            for c in page["contests"]:
                tier = c["decided_by"]
                tiers[tier] += 1
                cat[c["category"]] += 1
                per_row[row][tier] += 1
                ci, cj = c.get("conf_i"), c.get("conf_j")
                if not isinstance(ci, (int, float)) \
                        or not isinstance(cj, (int, float)):
                    continue
                loser_is_i = c["loser_staff"] == c["staff_i"]
                lose, win = (ci, cj) if loser_is_i else (cj, ci)
                if win == lose:
                    ties[tier] += 1
                    continue
                agree[(tier, win > lose)] += 1
                margins[tier].append(round(win - lose, 4))
    print(f"rows: {rows}   contested pairs: {sum(tiers.values())}")
    print("\n-- which tier decided --")
    for t, n in tiers.most_common():
        print(f"   {t:20s} {n:6d}  {n/max(1,sum(tiers.values())):6.1%}")
    print("\n-- category of the contested glyph --")
    for k, n in cat.most_common():
        print(f"   {k:20s} {n:6d}")

    print("\n-- DOES CONFIDENCE AGREE WITH THE TIER THAT DECIDED? --")
    print("   (ladder is the internal gold standard; 0.500 means "
          "confidence carries no ownership information)")
    for t in ("ladder", "range_or_hairpin", "distance"):
        yes = agree[(t, True)]
        no = agree[(t, False)]
        n = yes + no
        if not n:
            continue
        lo, hi = wilson(yes, n)
        m = sorted(abs(x) for x in margins[t])
        print(f"   {t:20s} n={n:6d} (+{ties[t]} exact ties)  "
              f"P(winner conf > loser conf) = {yes/n:.3f}  "
              f"95% CI [{lo:.3f}, {hi:.3f}]  "
              f"median |Δconf| = {m[len(m)//2]:.3f}")

    print("\n-- REACH of a confidence tie-break under rank 0 --")
    n = agree[("distance", True)] + agree[("distance", False)]
    for thr in (0.0, 0.05, 0.10, 0.20, 0.30):
        over = sum(1 for x in margins["distance"] if x < -thr)
        print(f"   |Δconf| > {thr:.2f}: confidence would OVERTURN distance on "
              f"{over:5d} of {n} distance-decided pairs  "
              f"({over/max(1,n):5.1%})")

    print("\n-- per row --")
    for row, c in sorted(per_row.items()):
        print(f"   {row:36s} " + "  ".join(f"{k}={v}"
                                           for k, v in sorted(c.items())))


if __name__ == "__main__":
    main()
