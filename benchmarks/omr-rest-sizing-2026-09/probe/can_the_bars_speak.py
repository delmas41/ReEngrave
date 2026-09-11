"""Is the ARBITER silent exactly where it is needed?

⚠️ THE HAZARD THIS IS ABOUT is recorded in CLAUDE.md as *"the bars are not an
independent umpire over a bad reading"*: the page that most needs a second
witness is the page whose ink is degraded, and the same degradation stops its
bars from summing. `_carry_meter` leans on this system's OWN bars to confirm a
carried meter, so a carry can be refused for want of bars rather than for being
wrong.

Here that hazard has a second, sharper edge peculiar to rests: `_bar_lengths_for`
excludes **every bar holding a whole rest**, deliberately, so that a rest whose
4.0 is our own default cannot vote for the meter that will re-size it. On a page
where most staves are resting, that exclusion removes most of the bars — and the
bars it removes are exactly the ones the repair is for.

So this counts, per system and BEFORE any arm is run, how many bars survive the
exclusion and could clear the quorum. It is a PREDICTION, and it is worth having
only because the arm can disagree with it.

⚠️ Every constant is IMPORTED from the decision, never restated.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Subject, Kind  # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (  # noqa: E402
    METER_CARRY_FLOOR, METER_CARRY_MIN_BARS, METER_CARRY_MIN_STAVES_PER_BAR,
    W_METER_BAR_FITS, W_METER_BAR_CONTRADICTS, W_METER_CARRIED)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--candidate", type=float, default=2.0,
                    help="the carried meter's length in quarter notes")
    args = ap.parse_args(argv)
    rec = json.loads(Path(args.record).read_text())["record"]

    print("constants (imported): floor=%s min_bars=%s min_staves=%s "
          "fits=%+g contradicts=%+g carried=%+g"
          % (METER_CARRY_FLOOR, METER_CARRY_MIN_BARS,
             METER_CARRY_MIN_STAVES_PER_BAR, W_METER_BAR_FITS,
             W_METER_BAR_CONTRADICTS, W_METER_CARRIED))

    superseded = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    standing = [v for v in rec["verdicts"] if v["id"] not in superseded]

    dur = {}
    whole_rest_cells = set()
    for v in standing:
        if v["quantity"] != "duration" or v["outcome"] != "decided":
            continue
        dur[v["subject"]] = v
        if (v.get("detail") or {}).get("rest") == "restWhole":
            c = Subject.from_key(v["subject"]).at(Kind.CELL)
            if c:
                whole_rest_cells.add(c.to_key())

    events = {v["subject"]: v for v in standing
              if v["quantity"] == "event" and v["outcome"] == "decided"}

    # system -> cell_index -> [per-staff bar totals]
    per_system = defaultdict(lambda: defaultdict(list))
    excluded = Counter()
    for cellkey, ev in events.items():
        cell = Subject.from_key(cellkey)
        sysk = cell.at(Kind.SYSTEM).to_key()
        if cellkey in whole_rest_cells:
            excluded[sysk] += 1
            continue
        total = 0.0
        for event in (ev.get("value") or {}).get("events", ()):
            beats = []
            for gi in event.get("glyphs") or ():
                g = Subject(Kind.GLYPH, page=cell.page, system=cell.system,
                            staff=cell.staff, cell=cell.cell, glyph=gi)
                d = dur.get(g.to_key())
                if d:
                    beats.append(float((d["value"] or {}).get("beats") or 0.0))
            if beats:
                total += Counter(beats).most_common(1)[0][0]
        if total > 0:
            per_system[sysk][cell.cell].append(round(total, 4))

    print("\n%-14s %-9s %-9s %-9s %-9s %s"
          % ("system", "bars w/", "excluded", "quorum", "agree/dis",
             "predicted support vs %s" % args.candidate))
    for sysk in sorted(per_system | excluded.keys()):
        bars = per_system.get(sysk, {})
        agree = dis = 0
        for _ci, lengths in sorted(bars.items()):
            if len(lengths) < METER_CARRY_MIN_STAVES_PER_BAR:
                continue
            mode, n = Counter(lengths).most_common(1)[0]
            if n / len(lengths) < 0.5:
                continue
            if abs(mode - args.candidate) < 1e-6:
                agree += 1
            else:
                dis += 1
        terms = agree + dis
        if terms < METER_CARRY_MIN_BARS:
            verdict = "too_few_assessable_bars (%d)" % terms
        else:
            support = (W_METER_CARRIED + agree * W_METER_BAR_FITS
                       + dis * W_METER_BAR_CONTRADICTS)
            verdict = ("%+.1f -> %s" % (
                support,
                "CARRIES" if support >= METER_CARRY_FLOOR
                else "refused (outweighed)"))
        print("%-14s %-9d %-9d %-9d %-9s %s"
              % (sysk, len(bars), excluded.get(sysk, 0), terms,
                 "%d/%d" % (agree, dis), verdict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
