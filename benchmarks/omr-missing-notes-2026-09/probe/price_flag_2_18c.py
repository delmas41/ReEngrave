"""ROADMAP 2.18c -- price the stem-tip flag-ink narrowing by RE-DECIDING one
saved record (a fresh gather of Breitkopf 317803 pdf p1, ON THIS TREE, so
`Q.STEM_TIP_INK` is on it).

PATH: STAGED. ADJUDICATE->EXPORT over a FIXED gather (`review.rerun.rerun`).
Arms, both on this tree, same record:

  * off -- `RH._stem_tip_flag_ink` forced to `(None, ())`: the population
    this item targets falls back to exactly today's (pre-2.18c) behaviour.
    This is the CONTROL: its census must equal a record decided with the
    quantity simply absent, i.e. this IS the 2.18b tree's own reading of
    every head this rule does not touch.
  * on  -- the tree as committed.

    python3 benchmarks/omr-missing-notes-2026-09/probe/price_flag_2_18c.py \\
        <record.json> --out <out.json>
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr.staged.adjudicators import rhythm as RH           # noqa: E402
from tools.omr.staged.record import Q                            # noqa: E402
from tools.omr.staged.review import rerun as RR                  # noqa: E402

KEYS = ("notes", "rests", "beams", "beamed_events", "bars_held_out_sum",
        "notes_held_out_sum", "bars_with_events")


def arm(record: str, name: str) -> dict:
    real = RH._stem_tip_flag_ink
    if name == "off":
        RH._stem_tip_flag_ink = lambda ev, cell, own_stems, side: (None, ())
    try:
        _d, result, _ing = RR.rerun(record, None, None)
    finally:
        RH._stem_tip_flag_ink = real
    _xml, rep, _ref, _placed = RR.export_with_subjects(result)
    standing = RR._verdict_index(result["record"]["verdicts"])
    dur = {s: v for (q, s), v in standing.items() if q == Q.DURATION}
    held = sorted({f'{b.get("page")}/{b.get("system")}/{b.get("staff")}/'
                   f'{b.get("cell")}'
                   for b in (rep.get("bars_held_out_sum") or {}).get("held")
                   or ()})
    return {
        "notes_in_file": _d_notes(dur),
        "duration_outcomes": dict(collections.Counter(
            f'{v["outcome"]}:{v.get("reason")}' for v in dur.values())),
        "notes_not_written": rep.get("notes_not_written"),
        "written": {k: (rep.get("written") or {}).get(k) for k in KEYS},
        "bars_held_by_sum": held,
        "durations": {s: {"outcome": v["outcome"], "reason": v.get("reason"),
                          "beats": (v.get("value") or {}).get("beats")
                          if isinstance(v.get("value"), dict) else None,
                          "candidates": [
                              {"beats": (c.get("value") or {}).get("beats"),
                               "support": c.get("support")}
                              for c in (v.get("candidates") or ())]
                          if v["outcome"] == "narrowed" else None}
                      for s, v in dur.items()},
    }


def _d_notes(dur: dict) -> int:
    return sum(1 for v in dur.values() if v["outcome"] == "decided")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    arms = {n: arm(a.record, n) for n in ("off", "on")}

    off, on = arms["off"], arms["on"]
    # ⚠️ THE CONTROL. Every duration this rule does not touch must decide
    # IDENTICALLY in both arms -- the OFF arm is what a record with no
    # `Q.STEM_TIP_INK` reading would have decided, and this rule may only
    # ever ADD a narrowing where OFF decided `head_and_marks` at the head
    # value; it may never move anything else.
    moved = {s: (off["durations"][s], on["durations"].get(s))
             for s in off["durations"]
             if off["durations"][s] != on["durations"].get(s)}
    control_ok = all(o["reason"] == "head_and_marks" and o["outcome"] ==
                     "decided" for o, _n in moved.values())
    print("CONTROL (every moved head was OFF's head_and_marks, nothing "
          "else moved): " + ("PASSED" if control_ok else "FAILED"))

    for k in ("duration_outcomes", "notes_not_written", "written",
              "notes_in_file"):
        print(f"\n{k}")
        for n in arms:
            print(f"  {n:5s} {arms[n][k]}")

    narrowed_new = {s: n for s, (o, n) in moved.items()
                    if n and n["outcome"] == "narrowed"
                    and n.get("reason") == "flag_ink_unread"}
    print(f"\nheads newly NARROWED flag_ink_unread: {len(narrowed_new)}")
    for s in sorted(narrowed_new):
        print(f"  {s}  {narrowed_new[s]['candidates']}")

    out = {"arms": {n: {k: v for k, v in arms[n].items() if k != "durations"}
                    for n in arms},
           "moved_off_to_on": moved,
           "narrowed_flag_ink_unread": narrowed_new}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {a.out}")
    return 0 if control_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
