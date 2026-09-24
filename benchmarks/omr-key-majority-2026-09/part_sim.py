"""ROADMAP 2.9b — price the CHANGE thresholds off a saved record.

    python3 benchmarks/omr-key-majority-2026-09/part_sim.py <record|arm.json>
    python3 benchmarks/omr-key-majority-2026-09/part_sim.py <...> --sweep

⚠️⚠️ **A SIMULATOR, NOT THE RULE.** It reads the key verdicts a record (or a
`readjudicate --out` arm) already holds and hands them to the SHIPPED
functions — `header.admitted_changes` and `header._segments` — under other
thresholds, so `CHANGE_MIN_WITNESSES`, `CHANGE_MIN_SHARE` and
`CHANGE_MIN_RUN` can be priced rather than chosen. It imports the shipped
defaults, so the two cannot drift apart silently.

What the sweep answers, and it is the question `[C24]` alone does not: the
registry's `MIN_WITNESSES = 2` says how many staves must agree, and says
nothing about a plate that under-counts the SAME amount on two parts at once.
The persistence columns price that.

⚠️ It is BLIND to what INFER then does with a filled value and to EXPORT's own
carry. The file's own `<key>` count is measured by `part_report.py` on the
real arm; this only chooses the constants.
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from tools.omr.staged.record_io import load_record            # noqa: E402
from tools.omr.staged.adjudicators import header as H         # noqa: E402
from tools.omr.key_consensus import (MAY_DIFFER_NOT_A_WITNESS,  # noqa: E402
                                     NO_SIGNATURE_CONVENTION)


def _fields(subject: str):
    p = subject.split("/")
    return int(p[1]), int(p[2]), int(p[3])


def read_parts(rec: dict):
    """`{slot: [((page, system), fifths or None)]}`, plus the slot names."""
    slots = {v["subject"]: v for v in rec["verdicts"]
             if v["quantity"] == "slot_index"}
    keys = {v["subject"]: v for v in rec["verdicts"]
            if v["quantity"] == "key_signature"}
    parts = collections.defaultdict(list)
    names = {}
    for sub, sv in slots.items():
        if sv["outcome"] != "decided" or not isinstance(sv["value"], int):
            continue
        slot = int(sv["value"])
        name = (sv.get("detail") or {}).get("instrument")
        if name and slot not in names:
            names[slot] = str(name)
        kv = keys.get(sub)
        value = kv["value"] if kv and kv["outcome"] == "decided" else None
        page, system, _staff = _fields(sub)
        parts[slot].append(((page, system), value))
    for slot in parts:
        parts[slot].sort()
    return dict(parts), names


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--sweep", action="store_true")
    a = ap.parse_args()

    rec = load_record(a.record)
    rec = rec["record"] if "record" in rec else rec
    parts, names = read_parts(rec)
    witnesses = {slot: rows for slot, rows in parts.items()
                 if names.get(slot) not in NO_SIGNATURE_CONVENTION
                 and names.get(slot) not in MAY_DIFFER_NOT_A_WITNESS}
    print(f"{len(parts)} parts, {len(witnesses)} may witness a change, "
          f"{sum(1 for r in parts.values() for _s, v in r if v is not None)} "
          f"decided readings")

    pairs = ([(w, s, r) for w in (2, 3) for s in (0.0, 0.5)
              for r in (1, 2, 3)] if a.sweep
             else [(H.CHANGE_MIN_WITNESSES, H.CHANGE_MIN_SHARE,
                    H.CHANGE_MIN_RUN)])
    for w, share, run in pairs:
        changes = H.admitted_changes(witnesses, min_witnesses=w,
                                     min_share=share, min_run=run)
        moved = filled = 0
        for slot, rows in parts.items():
            segs = H._segments(rows, changes)
            for sys_key, value in rows:
                want = H.segment_fifths(segs, sys_key)
                if want is None:
                    continue
                if value is None:
                    filled += 1
                elif value != want:
                    moved += 1
        mark = "   <-- SHIPPED" if (w, share, run) == (
            H.CHANGE_MIN_WITNESSES, H.CHANGE_MIN_SHARE,
            H.CHANGE_MIN_RUN) else ""
        print(f"witnesses>={w} share>={share} run>={run}: "
              f"changes={len(changes):3d}  part_dissent={moved:4d} "
              f"part_gaps={filled:4d}{mark}")
        if changes and len(changes) <= 8:
            print(f"      {changes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
