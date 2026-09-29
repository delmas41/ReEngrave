"""ROADMAP 2.18b -- price the flag-join tolerance and the beyond-the-tip rule by
RE-DECIDING one saved record (the same frozen Breitkopf p1 gather as 2.18).

PATH: STAGED. ADJUDICATE->EXPORT over a FIXED gather (`review.rerun.rerun`).
Arms, all on this tree:

  * OFF   -- `STEM_JOIN_TOLERANCE_SPACES = 0`: zero tolerance switches off all
    both connections at once (flag attachment falls back to box
    overlap; `_beyond_own_stem` refuses to act without a slack). This is the
    2.18 tree, and it is the CONTROL: its census must equal the 2.18 ON arm
    committed in `out/price_stem_side_p1.json`, or the probe exits 1.
  * FLAG  -- tolerance on, `_beyond_own_stem` forced to keep every stroke:
    the flag attachment only.
  * ALL   -- the tree as committed.

    python3 benchmarks/omr-missing-notes-2026-09/probe/price_2_18b.py \\
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
BASELINE = HERE / "out" / "price_stem_side_p1.json"


def arm(record: str, name: str) -> dict:
    real_tol, real_beyond = RH.STEM_JOIN_TOLERANCE_SPACES, RH._beyond_own_stem
    if name == "off":
        RH.STEM_JOIN_TOLERANCE_SPACES = 0.0
    if name == "flag":
        RH._beyond_own_stem = lambda beams, stems, att, side, tol: (
            list(beams), [])
    try:
        d, result, _ing = RR.rerun(record, None, None)
    finally:
        RH.STEM_JOIN_TOLERANCE_SPACES = real_tol
        RH._beyond_own_stem = real_beyond
    _xml, rep, _ref, _placed = RR.export_with_subjects(result)
    standing = RR._verdict_index(result["record"]["verdicts"])
    dur = {s: v for (q, s), v in standing.items() if q == Q.DURATION}
    held = sorted({f'{b.get("page")}/{b.get("system")}/{b.get("staff")}/'
                   f'{b.get("cell")}'
                   for b in (rep.get("bars_held_out_sum") or {}).get("held")
                   or ()})
    return {
        "notes_in_file": d.notes_after,
        "duration_outcomes": dict(collections.Counter(
            f'{v["outcome"]}:{v.get("reason")}' for v in dur.values())),
        "beam_evidence": dict(collections.Counter(
            (v.get("detail") or {}).get("beam_evidence")
            for v in dur.values() if v["outcome"] == "decided")),
        "heads_with_beyond_stem": sum(
            1 for v in dur.values()
            if (v.get("detail") or {}).get("beams_beyond_stem")),
        "notes_not_written": rep.get("notes_not_written"),
        "written": {k: (rep.get("written") or {}).get(k) for k in KEYS},
        "bars_held_by_sum": held,
        "durations": {s: {"outcome": v["outcome"], "reason": v.get("reason"),
                          "beats": (v.get("value") or {}).get("beats")
                          if isinstance(v.get("value"), dict) else None}
                      for s, v in dur.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    arms = {n: arm(a.record, n) for n in ("off", "flag", "all")}

    base = json.loads(BASELINE.read_text())["on"]
    ok = (arms["off"]["notes_not_written"] == base["notes_not_written"]
          and arms["off"]["notes_in_file"] == base["notes_in_file"]
          and arms["off"]["duration_outcomes"] == base["duration_outcomes"]
          and arms["off"]["bars_held_by_sum"] == base["bars_held_by_sum"])
    print("CONTROL (tolerance 0 reproduces the committed 2.18 arm): "
          + ("PASSED" if ok else "FAILED"))

    for k in ("duration_outcomes", "beam_evidence", "heads_with_beyond_stem",
              "notes_not_written", "written", "notes_in_file"):
        print(f"\n{k}")
        for n in arms:
            print(f"  {n:5s} {arms[n][k]}")
    off, al = arms["off"], arms["all"]
    a_, b_ = set(off["bars_held_by_sum"]), set(al["bars_held_by_sum"])
    print(f"\nbars held by the sum: off {len(a_)}, all {len(b_)}; newly held "
          f"{sorted(b_ - a_)}; released {sorted(a_ - b_)}")
    changed = {s: (off["durations"][s], al["durations"].get(s))
               for s in off["durations"]
               if off["durations"][s] != al["durations"].get(s)}
    print(f"durations changed off -> all: {len(changed)}")
    out = {"arms": {n: {k: v for k, v in arms[n].items() if k != "durations"}
                    for n in arms},
           "changed_off_to_all": changed,
           "changed_off_to_flag": {
               s: (off["durations"][s], arms["flag"]["durations"].get(s))
               for s in off["durations"]
               if off["durations"][s] != arms["flag"]["durations"].get(s)}}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {a.out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
