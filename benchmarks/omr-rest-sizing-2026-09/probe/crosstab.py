"""The cross-tab the headline table cannot give: METER x ELIGIBILITY.

`reach.py` shows the two wrong lengths and their glyphs. This asks the
question a repair needs answered: of the rests the `size_measure_rest`
convention COVERS -- a lone, dotless `restWhole` standing alone in its bar --
how many stand on a system whose meter was DECIDED and how many on one that
ABSTAINED? The first group is a rule fault; the second is a meter fault.

It also counts the bars the record holds NO duration for at all, because the
exporter pads those with a measure rest of its own and they are invisible to a
probe that only looks at rows that exist.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Subject, Kind  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    args = ap.parse_args(argv)
    rec = json.loads(Path(args.record).read_text())["record"]

    vrd = rec["verdicts"]
    superseded = {v["supersedes"] for v in vrd if v.get("supersedes")}
    standing = [v for v in vrd if v["id"] not in superseded]

    meters = {v["subject"]: v for v in standing if v["quantity"] == "meter"}

    def meter_state(cellkey):
        s = Subject.from_key(cellkey).at(Kind.SYSTEM)
        m = meters.get(s.to_key() if s else None)
        if m is None:
            return "no meter ROW at all"
        val = m.get("value") or {}
        if m["outcome"] == "decided" and val.get("numerator"):
            return "DECIDED %s/%s" % (val["numerator"], val["denominator"])
        return "abstained: %s" % m["reason"]

    dur_by_cell = defaultdict(list)
    for v in standing:
        if v["quantity"] != "duration":
            continue
        c = Subject.from_key(v["subject"]).at(Kind.CELL)
        if c:
            dur_by_cell[c.to_key()].append(v)

    # every cell the record knows about at all, from any quantity
    all_cells = set()
    for row in rec["observations"] + rec.get("abstentions", []) + vrd:
        c = Subject.from_key(row["subject"]).at(Kind.CELL)
        if c:
            all_cells.add(c.to_key())

    tab = defaultdict(Counter)
    for cellkey in sorted(all_cells):
        ms = meter_state(cellkey)
        rows = [v for v in dur_by_cell.get(cellkey, ())
                if v["outcome"] == "decided"]
        if not rows:
            tab[ms]["BAR with no decided duration (exporter pads it)"] += 1
            continue
        rests = [v for v in rows
                 if isinstance(v.get("value"), dict)
                 and v["value"].get("is_rest")]
        if len(rows) == 1 and len(rests) == 1:
            r = rests[0]
            glyph = (r.get("detail") or {}).get("rest", "?")
            if glyph == "restWhole" and not r["value"].get("dots"):
                key = ("lone restWhole, SIZED"
                       if r["value"].get("measure_rest")
                       else "lone restWhole, NOT sized")
            else:
                key = "lone rest, glyph %s (rule excludes)" % glyph
            tab[ms][key] += 1
        else:
            tab[ms]["bar holds %d durations" % len(rows)] += 1

    print("=== CELLS, by the meter of their system ===")
    for ms in sorted(tab, key=lambda k: -sum(tab[k].values())):
        print("\n  %s   (%d cells)" % (ms, sum(tab[ms].values())))
        for k, n in tab[ms].most_common():
            print("      %5d  %s" % (n, k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
