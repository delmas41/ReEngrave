"""REACH FIRST: which rests come out the wrong length, and which sub-population.

Reads a saved staged record and reports, before any repair is attempted:
  * every system's METER verdict -- outcome, reason, value;
  * every standing rest DURATION -- its glyph, its beats, whether it carries
    `measure_rest`;
  * the CELL each stands in, and whether that cell is the LONE-REST bar the
    `size_measure_rest` convention covers.

⚠️ It reports the two wrong lengths APART. A rest at the glyph's nominal 4.0
and a rest at 1.0 are different faults and merging them would hide whichever is
smaller.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.omr.staged.record import Subject, Kind  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text())["record"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--bar-beats", type=float, default=2.0,
                    help="the PRINTED bar length, hand-read (2/4 -> 2.0)")
    args = ap.parse_args(argv)
    rec = load(args.record)

    vrd = rec["verdicts"]
    superseded = {v["supersedes"] for v in vrd if v.get("supersedes")}
    standing = [v for v in vrd if v["id"] not in superseded]

    # --- the meter, per system -------------------------------------------
    meters = {}
    for v in standing:
        if v["quantity"] != "meter":
            continue
        meters[v["subject"]] = v
    print("=== METER, per system ===")
    for k in sorted(meters):
        v = meters[k]
        val = v.get("value") or {}
        print("  %-14s %-9s %-34s %s/%s" % (
            k, v["outcome"], v["reason"],
            val.get("numerator"), val.get("denominator")))
    print()

    # --- durations --------------------------------------------------------
    by_cell = defaultdict(list)
    for v in standing:
        if v["quantity"] != "duration":
            continue
        sub = Subject.from_key(v["subject"])
        c = sub.at(Kind.CELL)
        by_cell[c.to_key() if c else None].append(v)

    lengths = Counter()
    pop = Counter()
    by_len_pop = defaultdict(Counter)
    meter_of_len = defaultdict(Counter)
    glyph_of_len = defaultdict(Counter)
    for cellkey, rows in by_cell.items():
        decided = [v for v in rows if v["outcome"] == "decided"]
        rests = [v for v in decided
                 if isinstance(v.get("value"), dict)
                 and v["value"].get("is_rest")]
        lone = (len(decided) == 1 and len(rests) == 1)
        sysk = None
        if cellkey:
            s = Subject.from_key(cellkey).at(Kind.SYSTEM)
            sysk = s.to_key() if s else None
        m = meters.get(sysk)
        mval = (m or {}).get("value") or {}
        if mval.get("numerator"):
            mstr = "%s/%s" % (mval.get("numerator"), mval.get("denominator"))
        else:
            mstr = (m or {}).get("reason", "NO_METER_VERDICT")
        for v in rests:
            beats = float((v["value"] or {}).get("beats") or 0.0)
            lengths[beats] += 1
            glyph = (v.get("detail") or {}).get("rest", "?")
            if v["value"].get("measure_rest"):
                bucket = "sized_by_the_rule"
            elif lone and glyph == "restWhole" and not v["value"].get("dots"):
                bucket = "LONE restWhole, rule did NOT fire"
            elif lone:
                bucket = "lone but not a plain restWhole (%s)" % glyph
            else:
                bucket = "not a lone rest (%d durations in the bar)" % len(decided)
            pop[bucket] += 1
            by_len_pop[beats][bucket] += 1
            meter_of_len[beats][mstr] += 1
            glyph_of_len[beats][glyph] += 1

    total = sum(lengths.values())
    wrong = sum(n for b, n in lengths.items()
                if abs(b - args.bar_beats) > 1e-6)
    print("=== REST DURATIONS: %d standing, %d not the printed bar "
          "length (%s) ===" % (total, wrong, args.bar_beats))
    for b, n in sorted(lengths.items(), key=lambda t: -t[1]):
        mark = "OK " if abs(b - args.bar_beats) < 1e-6 else "!! "
        print("  %s%6s ql  x%d" % (mark, b, n))
        for k, c in glyph_of_len[b].most_common():
            print("          glyph %-16s x%d" % (k, c))
        for k, c in meter_of_len[b].most_common():
            print("          meter %-26s x%d" % (k, c))
        for k, c in by_len_pop[b].most_common():
            print("          pop   %-50s x%d" % (k, c))
    print()
    print("=== SUB-POPULATION, all rests ===")
    for k, n in pop.most_common():
        print("  %5d  %s" % (n, k))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
