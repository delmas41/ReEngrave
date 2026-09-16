"""WHERE a bar loses its voice: the whole-rest exclusion, the STAFF quorum, or
the majority rule.

⚠️ `METER_CARRY_MIN_STAVES_PER_BAR = 3` is set BY ANALOGY to
`METER_COVERAGE_FLOOR`, and CLAUDE.md records that it "has never been measured
at all". This measures what it COSTS -- not what it should be. A constant this
document cannot price is left alone; naming its price is the contribution.

Three gates stand between "a bar the record holds durations for" and "a bar
that may vote on the meter", and they are reported APART because they have
different repairs:

  1. the WHOLE-REST exclusion (`_bar_lengths_for`) -- the fixpoint guard. A bar
     holding any whole rest may not vote, because its 4.0 is our own default
     for want of a meter and `size_measure_rest` will rewrite it FROM the
     answer. Widening this is REFUSED; it is what keeps the loop open.
  2. the STAFF quorum (`METER_CARRY_MIN_STAVES_PER_BAR`) -- fewer than this
     many staves read the bar at all.
  3. the MAJORITY rule -- the staves that did read it do not agree with EACH
     OTHER (`n / len(lengths) < 0.5`).

⚠️ This is an OFFLINE replica, like `can_the_bars_speak.py`, and inherits that
probe's recorded limitation: it reads the record's SAVED groupings and
post-consequence durations while a live run re-derives them. It is a SCREEN,
not a substitute for an arm.

⚠️ Every constant is IMPORTED from the decision, never restated.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Subject, Kind            # noqa: E402
from tools.omr.staged.adjudicators.rhythm import (           # noqa: E402
    METER_CARRY_MIN_STAVES_PER_BAR)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero when the instrument assessed NOTHING")
    a = ap.parse_args(argv)
    rec = json.loads(Path(a.record).read_text())["record"]

    print("constant (imported): METER_CARRY_MIN_STAVES_PER_BAR = %d"
          % METER_CARRY_MIN_STAVES_PER_BAR)

    sup = {v["supersedes"] for v in rec["verdicts"] if v.get("supersedes")}
    standing = [v for v in rec["verdicts"] if v["id"] not in sup]

    dur, whole_rest_cells = {}, set()
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

    per_sys = defaultdict(lambda: defaultdict(list))
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
            per_sys[sysk][cell.cell].append(round(total, 4))

    print("\n%-14s %9s %6s %9s %9s %6s" % (
        "system", "excl(WR)", "bars", "lost:min", "lost:maj", "VOTE"))
    tot = Counter()
    for sysk in sorted(set(per_sys) | set(excluded)):
        bars = per_sys.get(sysk, {})
        lost_min = lost_maj = voting = 0
        for _ci, lengths in sorted(bars.items()):
            if len(lengths) < METER_CARRY_MIN_STAVES_PER_BAR:
                lost_min += 1
                continue
            _mode, n = Counter(lengths).most_common(1)[0]
            if n / len(lengths) < 0.5:
                lost_maj += 1
                continue
            voting += 1
        print("%-14s %9d %6d %9d %9d %6d" % (
            sysk, excluded[sysk], len(bars), lost_min, lost_maj, voting))
        tot["excluded"] += excluded[sysk]
        tot["bars"] += len(bars)
        tot["min"] += lost_min
        tot["maj"] += lost_maj
        tot["vote"] += voting

    print("%-14s %9d %6d %9d %9d %6d" % (
        "TOTAL", tot["excluded"], tot["bars"], tot["min"], tot["maj"],
        tot["vote"]))

    denom = tot["excluded"] + tot["bars"]
    if denom:
        print("\nof %d bars the record holds events for:" % denom)
        print("  %5d (%5.1f%%) hold a WHOLE REST   -- the fixpoint guard"
              % (tot["excluded"], 100.0 * tot["excluded"] / denom))
        print("  %5d (%5.1f%%) read by < %d staves  -- the STAFF quorum"
              % (tot["min"], 100.0 * tot["min"] / denom,
                 METER_CARRY_MIN_STAVES_PER_BAR))
        print("  %5d (%5.1f%%) staves disagree      -- the MAJORITY rule"
              % (tot["maj"], 100.0 * tot["maj"] / denom))
        print("  %5d (%5.1f%%) MAY VOTE"
              % (tot["vote"], 100.0 * tot["vote"] / denom))

    if a.check:
        # ⚠️ Same contract as `bar_fill.py`: this fails when the INSTRUMENT
        # assessed nothing, and NEVER on a threshold. A silence figure used as
        # a gate would be gamed by reading FEWER bars.
        if denom == 0:
            print("\nINSTRUMENT DEAD: the record holds no bar with events.")
            return 1
        print("\ninstrument LIVE: %d bars assessed" % denom)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
