"""Is a rest the detector called `restQuarter` SHAPED like a quarter rest?

Sean's observation names two lengths and this repo has twice found that a
length complaint was a CLASS complaint underneath. A whole rest is a short
wide filled rectangle hanging under the fourth line; a quarter rest is a tall
narrow squiggle spanning most of the staff. Their aspect ratios do not
overlap, which makes this a shape question with no truth file -- the same move
`audit_ledger_zone_labels.py` makes for noteheads.

⚠️ IT NAMES NO ERRORS AND CANNOT. A box tall enough to be a quarter rest is
not thereby a correct reading, and this says nothing about the ink inside it.
It reports the two populations' DISTRIBUTIONS and whether they separate; where
they do not, the class is not the lever and a length repair aimed at them
would be aimed at nothing.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Subject, Kind  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    args = ap.parse_args(argv)
    rec = json.loads(Path(args.record).read_text())["record"]

    boxes, confs = {}, {}
    for o in rec["observations"]:
        if o["quantity"] == "glyph_box":
            boxes[o["subject"]] = o["value"]
        elif o["quantity"] == "glyph_conf":
            confs[o["subject"]] = o["value"]

    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    pops = defaultdict(list)
    for v in rec["verdicts"]:
        if v["quantity"] != "duration" or v["id"] in superseded:
            continue
        if v["outcome"] != "decided":
            continue
        val = v.get("value") or {}
        if not val.get("is_rest"):
            continue
        glyph = (v.get("detail") or {}).get("rest")
        # ⚠️ `glyph_box` is `[class, x, y, WIDTH, HEIGHT]`, not corners. The
        # two spellings agree in every coordinate at the origin, which is the
        # frame error this repo has already paid for once.
        b = boxes.get(v["subject"])
        if not b or len(b) != 5:
            continue
        w = float(b[3])
        h = float(b[4])
        if w <= 0 or h <= 0:
            continue
        pops[glyph].append((h / w, w, h, confs.get(v["subject"])))

    print("%-14s %-6s  %-28s %-22s %s"
          % ("glyph", "n", "aspect h/w  (p10 med p90)", "median w x h", "med conf"))
    for glyph in sorted(pops, key=lambda g: -len(pops[g])):
        rows = pops[glyph]
        asp = sorted(r[0] for r in rows)
        n = len(asp)
        p10, p90 = asp[max(0, n // 10)], asp[min(n - 1, (9 * n) // 10)]
        cf = [r[3] for r in rows if r[3] is not None]
        print("%-14s %-6d  %5.2f %5.2f %5.2f            %5.0f x %-5.0f      %s"
              % (glyph, n, p10, statistics.median(asp), p90,
                 statistics.median(r[1] for r in rows),
                 statistics.median(r[2] for r in rows),
                 ("%.2f" % statistics.median(cf)) if cf else "-"))

    w, q = pops.get("restWhole", []), pops.get("restQuarter", [])
    if w and q:
        wa = sorted(r[0] for r in w)
        qa = sorted(r[0] for r in q)
        print("\nSEPARATION on aspect (h/w): restWhole max %.2f, "
              "restQuarter min %.2f -> %s"
              % (wa[-1], qa[0],
                 "EMPTY INTERVAL" if qa[0] > wa[-1] else "THEY OVERLAP"))
        overlap = sum(1 for a in qa if a <= wa[-1])
        print("   restQuarter boxes inside the restWhole range: %d of %d"
              % (overlap, len(qa)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
