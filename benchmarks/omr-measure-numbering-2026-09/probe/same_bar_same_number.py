"""The SEMANTIC half: does a number now select the same PRINTED bar everywhere?

The byte control says the music did not move. It cannot say the numbers moved
to the RIGHT place -- a renumbering that added 1000 to every bar of P9 would
pass it. Two questions here, and neither needs a truth file:

  1. **Renaming, not reordering.** The n-th measure of each part must be the
     same music in both files, differing only in its `number=`. That is what
     makes this a relabelling of the bars we already had.
  2. **One number, one instant.** For each printed system, the set of numbers
     the parts standing on it carry must be a SINGLE range. Before: p4/s0 is
     `82..96` for P1-P8 and `64..78` for P9-P11 -- two ranges, one system.

⚠️ (2) is checked against `export.build`'s OWN `StaffRun`s, called rather than
re-derived, so it cannot drift from the file -- and then asserted against the
emitted XML, because a reconstruction that quietly disagreed with the file is
the failure mode `export_arm.py`'s own control exists for.

    python3 .../probe/same_bar_same_number.py --record REC \
        --before out/before.musicxml --after out/after.musicxml
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.omr.staged import export as sx            # noqa: E402


def part_measures(path: Path):
    root = ET.parse(str(path)).getroot()
    return collections.OrderedDict(
        (p.get("id"), p.findall("measure")) for p in root.findall("part"))


def blob(m) -> str:
    m = ET.fromstring(ET.tostring(m))
    m.set("number", "#")
    return ET.tostring(m, encoding="unicode")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    args = ap.parse_args(argv)

    problems = []

    # ── 1. renaming, not reordering ─────────────────────────────────────────
    b = part_measures(Path(args.before))
    a = part_measures(Path(args.after))
    print("=" * 74)
    print("1. RENAMING, NOT REORDERING -- the n-th bar of each part")
    print("=" * 74)
    same = diff = 0
    for pid in b:
        if pid not in a or len(b[pid]) != len(a[pid]):
            problems.append("%s: different measure count" % pid)
            continue
        for mb, ma in zip(b[pid], a[pid]):
            if blob(mb) == blob(ma):
                same += 1
            else:
                diff += 1
    print("  identical at the same ordinal : %d" % same)
    print("  DIFFERENT                     : %d" % diff)
    if diff:
        problems.append("%d measures changed content" % diff)

    # ── 2. one number, one instant ──────────────────────────────────────────
    rec = sx.Record(json.loads(Path(args.record).read_text()))
    parts = sx.build(rec)[0]
    print()
    print("=" * 74)
    print("2. ONE NUMBER, ONE INSTANT -- the numbers each system's parts carry")
    print("=" * 74)
    print("%-9s %7s   %-22s %s" % ("system", "staves", "BEFORE (per-part)",
                                   "AFTER (document)"))

    def ranges(xmlmap, per_part_first):
        """{(page,system): {(lo,hi)}} read out of the FILE, not recomputed."""
        out = collections.defaultdict(set)
        for pi, part in enumerate(parts):
            pid = "P%d" % (pi + 1)
            ms = xmlmap.get(pid, [])
            at = 0
            for run in part:
                if run.n_measures == 0:
                    continue
                window = ms[at:at + run.n_measures]
                at += run.n_measures
                nums = [int(m.get("number")) for m in window]
                out[(run.page, run.system)].add((nums[0], nums[-1]))
            if at != len(ms):
                problems.append("%s: %d runs' bars vs %d in the file"
                                % (pid, at, len(ms)))
        return out

    before_r = ranges(b, True)
    after_r = ranges(a, False)
    for key in sorted(after_r):
        nb = sorted(before_r[key])
        na = sorted(after_r[key])
        n_staves = sum(1 for part in parts for run in part
                       if (run.page, run.system) == key and run.n_measures)
        print("p%d/s%-6d %7d   %-22s %s"
              % (key[0], key[1], n_staves,
                 " ".join("%d-%d" % r for r in nb),
                 " ".join("%d-%d" % r for r in na)))
        if len(na) != 1:
            problems.append("p%d/s%d: %d different number ranges AFTER"
                            % (key[0], key[1], len(na)))
    split_before = sum(1 for k in before_r if len(before_r[k]) != 1)
    split_after = sum(1 for k in after_r if len(after_r[k]) != 1)
    print()
    print("  systems whose parts disagree about the numbers:  "
          "BEFORE %d of %d, AFTER %d of %d"
          % (split_before, len(before_r), split_after, len(after_r)))

    print()
    if problems:
        for p in problems[:20]:
            print("FAIL: " + p)
        return 1
    print("PASS: every bar kept its music, and every system now carries "
          "exactly ONE range of numbers across its parts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
