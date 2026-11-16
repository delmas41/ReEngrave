"""ROADMAP 2.311 -- WHY A RED BAR IS RED: the first cause of every red-marked bar on the count pages, from the record.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11 python3 benchmarks/note-loss-funnel-2026-11/redbars.py FACTS.json \
        --plate brahms --pages 0,4,... [--sample 20 --seed 2311 --crops DIR] [--json OUT]

A red-marked bar is every bar the export report lists as drawn red: `bars_written_red` (notes kept, "does not add up"),
`unread_empty_bars` (nothing written: "unread"), `bars_held_out_sum.held` (read, emptied) and `partial_bars` with status
partial (a red gap). The bar is (page, system, staff, cell); its marks are the record's glyph boxes with that key prefix.

FIRST CAUSE, in this order (each the record's own words; the order is ours and is said here so it can be argued):
  1 staff     a mark in the bar was dropped because its STAFF was not identified / has no measures (EXPORT) -- the
              whole staff is lost, so nothing else in the bar matters
  2 lost      a head or rest in the bar was read and NOT written for a reason that may hide a real mark (any fate not
              in export._NOT_A_GAP_REASONS): the most common such fate is named
  3 nothing   no head or rest box at all in the bar (the detector drew none: an empty-looking bar)
  4 all-twin  every head/rest box was refused as another mark's ink or a twin (in _NOT_A_GAP_REASONS) and nothing written
  5 sum       every read mark was written and the bar still does not add up: short / long against the meter in force
              (carried or printed), i.e. a value read wrong, a mark never boxed, or the meter wrong -- the record cannot
              tell which; the crop look decides on the sample
"""
from __future__ import annotations

import argparse
import collections
import json
import random
from pathlib import Path

from tools.omr.staged.export import _NOT_A_GAP_REASONS

STAFF_LOST = {"staff_not_identified", "owner_staff_has_no_measures"}


def red_bars(f: dict, pages: set) -> list:
    out, seen = [], {}
    for kind, lst in (("does_not_add_up", f["bars"]["red_not_add_up"]), ("unread_empty", f["bars"]["unread_empty"]),
                      ("held", f["bars"]["held"]), ("partial", [b for b in f["bars"]["partial"] if b.get("status") == "partial"])):
        for b in lst:
            if b.get("page") in pages and not b.get("doubled_staff_copy"):
                k = (b["page"], b["system"], b["staff"], b["cell"])
                if k in seen:          # one bar in two lists (e.g. a partial gap in a bar that also does not add up)
                    seen[k]["also"] = seen[k].get("also", []) + [kind]
                    continue
                seen[k] = dict(b, kind=kind)
                out.append(seen[k])
    return out


def cause_of(b: dict, cells: dict) -> tuple:
    key = (b["page"], b["system"], b["staff"], b["cell"])
    marks = [g for g in cells.get(key, ()) if g["head"] or g["rest"]]
    fates = [g["fate"] or "no_fate" for g in marks]
    if any(x in STAFF_LOST for x in fates):
        return "1 staff", next(x for x in fates if x in STAFF_LOST)
    lost = [x for x in fates if x not in ("written", "written_relocated") and x not in _NOT_A_GAP_REASONS]
    if lost:
        return "2 lost", collections.Counter(lost).most_common(1)[0][0]
    if not marks:
        return "3 nothing", "no head or rest box in the bar"
    if not any(x in ("written", "written_relocated") for x in fates):
        return "4 all-twin", collections.Counter(fates).most_common(1)[0][0]
    if b["kind"] == "does_not_add_up":
        want, got = b.get("want_quarters"), b.get("counted_quarters") or []
        if want is not None and got:
            side = "short" if max(got) < want else ("long" if min(got) > want else "two voices disagree")
            return "5 sum", "%s (want %s, counted %s)" % (side, want, "/".join("%g" % x for x in got))
    return "5 sum", "%s with every read mark written" % b["kind"]


def run(f: dict, pages: set) -> list:
    cells = collections.defaultdict(list)
    for k, g in f["glyphs"].items():
        p = k.split("/")
        if len(p) == 6:
            cells[(int(p[1]), int(p[2]), int(p[3]), int(p[4]))].append(dict(g, key=k))
    bars = red_bars(f, pages)
    for b in bars:
        b["cause"], b["why"] = cause_of(b, cells)
    return bars


def render(bars: list, title: str) -> str:
    out = ["%s: %d red-marked bars" % (title, len(bars)), "  by kind: %s" % dict(collections.Counter(b["kind"] for b in bars))]
    c = collections.Counter(b["cause"] for b in bars)
    for k in sorted(c):
        out.append("  %-12s %4d  %5.1f%%" % (k, c[k], 100.0 * c[k] / max(1, len(bars))))
        w = collections.Counter(b["why"].split(" (")[0] for b in bars if b["cause"] == k)
        for kk, v in w.most_common(6):
            out.append("      %-50s %4d" % (kk, v))
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("facts")
    ap.add_argument("--plate", required=True)
    ap.add_argument("--pages", required=True)
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2311)
    ap.add_argument("--json")
    a = ap.parse_args()
    pages = {int(x) for x in a.pages.split(",")}
    f = json.load(open(a.facts))
    bars = run(f, pages)
    print(render(bars, "%s, ALL" % a.plate))
    rng = random.Random(a.seed)
    order = sorted(bars, key=lambda b: (b["page"], b["system"], b["staff"], b["cell"]))
    sample = rng.sample(order, min(a.sample, len(order)))
    print(render(sample, "%s, SAMPLE of %d (seed %d)" % (a.plate, len(sample), a.seed)))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(all=bars, sample=sample), default=str, indent=0))


if __name__ == "__main__":
    main()
