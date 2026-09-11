"""THE EXACT PARTITION of 111 / 93 / 16, and which instrument each part holds.

Sean read the first cleanup artefact and said *"none of the measure math makes
sense."* That is a symptom. This turns it into an accounting identity and then
into a mechanism, to the measure and to the staff-system -- the standard
`benchmarks/omr-part-join-2026-09` set when it separated `entire staff` into
four causes summing to the bucket EXACTLY (14,992 vs 14,992, 0 unexplained).

Two inputs, and NEITHER is re-derived here:

  * `out/system-map-p1-p4.json` from `benchmarks/omr-cleanup-count-2026-09` --
    the EXPORTER'S OWN emitted mapping of exported measures to printed
    systems, asserted measure-for-measure against the XML when it was made.
    So the part totals below are the file's, not a reconstruction of it.
  * `printed-lineups.json` -- which instrument each printed staff carries,
    from a hand-read source corroborated by the page's own margin labels.

`--check` exits non-zero if the partition does not balance.

    python3 benchmarks/omr-part-join-phase2-2026-09/probe/partition.py --check
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent

SYSTEM_MAP = REPO / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"
LINEUPS = HERE / "printed-lineups.json"


def load():
    return json.loads(SYSTEM_MAP.read_text()), json.loads(LINEUPS.read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    smap, lin = load()
    lineup_of = {(s["page"], s["system"]): s["lineup"] for s in lin["systems"]}
    problems = []

    # ── 1. the systems, as printed and as read ──────────────────────────────
    print("=" * 78)
    print("1. THE SYSTEMS")
    print("=" * 78)
    print("%-10s %7s %9s   %s" % ("system", "staves", "bars/staff", "lineup"))
    sys_rows = []
    for sd in smap["systems"]:
        key = (sd["page"], sd["system"])
        bars = {st["n_measures"] for st in sd["staves"]}
        n = len(sd["staves"])
        printed = lineup_of.get(key)
        sys_rows.append((key, n, sorted(bars)[0] if len(bars) == 1 else None))
        print("p%d/s%-6d %7d %9s   %s"
              % (key[0], key[1], n,
                 sorted(bars)[0] if len(bars) == 1 else sorted(bars),
                 "%d printed" % len(printed) if printed else "UNKNOWN"))
        if printed is not None and len(printed) != n:
            problems.append(
                "p%d/s%d: we read %d staves, the print carries %d"
                % (key[0], key[1], n, len(printed)))
        if len(bars) != 1:
            problems.append("p%d/s%d: staves disagree about bar count: %s"
                            % (key[0], key[1], sorted(bars)))

    # ── 2. the partition ────────────────────────────────────────────────────
    per_part = collections.defaultdict(list)
    for sd in smap["systems"]:
        for st in sd["staves"]:
            per_part[st["part_index"]].append(
                ((sd["page"], sd["system"]), st["staff"], st["n_measures"]))

    print()
    print("=" * 78)
    print("2. THE PARTITION -- every part's measures, and where they came from")
    print("=" * 78)
    all_systems = [r[0] for r in sys_rows]
    bars_of = {k: b for k, _n, b in sys_rows}
    total_measures = 0
    by_total = collections.Counter()
    print("%-5s %7s   %s" % ("part", "meas", "  ".join(
        "p%d/s%d" % k for k in all_systems)))
    for pi in sorted(per_part):
        got = {k: n for k, _st, n in per_part[pi]}
        tot = sum(got.values())
        total_measures += tot
        by_total[tot] += 1
        cells = []
        for k in all_systems:
            cells.append("%5s" % (got[k] if k in got else "  --"))
        print("P%-4d %7d   %s" % (pi + 1, tot, " ".join(cells)))

    print()
    print("   histogram:", dict(sorted(by_total.items(), reverse=True)))

    # ── 3. the accounting identity ──────────────────────────────────────────
    print()
    print("=" * 78)
    print("3. THE IDENTITY -- a part is short by exactly the systems it misses")
    print("=" * 78)
    full = sum(bars_of[k] for k in all_systems)
    print("   a part present on every system holds  %d measures" % full)
    for pi in sorted(per_part):
        present = {k for k, _st, _n in per_part[pi]}
        missing = [k for k in all_systems if k not in present]
        tot = sum(n for _k, _st, n in per_part[pi])
        shortfall = sum(bars_of[k] for k in missing)
        ok = (tot + shortfall == full)
        if not ok:
            problems.append("P%d: %d + %d != %d" % (pi + 1, tot, shortfall, full))
        print("   P%-3d %4d = %d - %-3d  missing %s%s"
              % (pi + 1, tot, full, shortfall,
                 ", ".join("p%d/s%d" % k for k in missing) or "nothing",
                 "" if ok else "   <-- DOES NOT BALANCE"))

    staff_systems = sum(n for _k, n, _b in sys_rows)
    print()
    print("   total measures in the file : %d" % total_measures)
    print("   total staff-systems        : %d" % staff_systems)

    # ── 4. the graft ────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print("4. THE GRAFT -- which staff-systems the join put on another part")
    print("=" * 78)
    print("A part's instrument is taken from the FIRST system it appears on.")
    print("Every later staff-system whose printed instrument differs is a")
    print("span of one instrument's music filed under another's <part>.")
    print()
    def _players(name):
        """The players a printed staff label names.

        ⚠️ DERIVED FROM THE LABEL, NOT HAND-LISTED. `Violoncello e Basso` is
        one staff carrying two players, and the engraving says so in the word
        `e`. That is a CONDENSATION, not a graft: the part still holds the
        music of the player it was anchored on. Splitting them out matters --
        a graft is wrong notes on the wrong instrument and a condensation is
        a staff-count fact -- and conflating them inflates the count."""
        return {p.strip() for p in name.split(" e ")}

    grafts, condensations = [], []
    for pi in sorted(per_part):
        entries = sorted(per_part[pi], key=lambda e: all_systems.index(e[0]))
        anchor_key, anchor_staff, _ = entries[0]
        anchor = lineup_of[anchor_key][anchor_staff]
        for key, staff, n in entries[1:]:
            got = lineup_of[key][staff]
            if got == anchor:
                continue
            row = (pi, anchor, key, staff, got, n)
            (condensations if _players(anchor) & _players(got)
             else grafts).append(row)

    print("%-5s %-22s %-9s %-24s %s" % ("part", "part's instrument",
                                        "system", "printed there", "bars"))
    for pi, anchor, key, staff, got, n in grafts:
        print("P%-4d %-22s p%d/s%-6d %-24s %d"
              % (pi + 1, anchor, key[0], key[1], got, n))
    print()
    print("   GRAFTED staff-systems (a different instrument): %d of %d"
          % (len(grafts), staff_systems))
    by_system = collections.Counter("p%d/s%d" % k for _p, _a, k, _s, _g, _n
                                    in grafts)
    print("   by system:", dict(by_system))

    print()
    print("   reported apart -- CONDENSATION, the same player on a shared")
    print("   staff, which is not a wrong instrument:")
    for pi, anchor, key, staff, got, n in condensations:
        print("     P%-4d %-22s p%d/s%-6d %-24s %d"
              % (pi + 1, anchor, key[0], key[1], got, n))
    print("   condensation staff-systems: %d" % len(condensations))

    # ── 5. what a CORRECT join would give ───────────────────────────────────
    print()
    print("=" * 78)
    print("5. ⚠️  WHAT A CORRECT JOIN WOULD GIVE -- and it is not equal parts")
    print("=" * 78)
    print("Grouping each printed staff-system under the instrument the PAGE")
    print("prints there, with no join error at all:")
    print()
    by_instrument = collections.defaultdict(int)
    for sd in smap["systems"]:
        key = (sd["page"], sd["system"])
        for st in sd["staves"]:
            by_instrument[lineup_of[key][st["staff"]]] += st["n_measures"]
    order = {name: i for i, name in enumerate(lin["full"])}
    for name in sorted(by_instrument, key=lambda n: order.get(n, 99)):
        print("   %-24s %4d" % (name, by_instrument[name]))
    print()
    print("   ⚠️ The spread does NOT close. A tacet instrument has no printed")
    print("   staff, so a correct join gives it FEWER measures, not the same")
    print("   number -- and the parts that read 111 today read 111 BECAUSE")
    print("   the graft lends them another instrument's bars.")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
    else:
        print("The partition balances exactly, on every part.")

    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
