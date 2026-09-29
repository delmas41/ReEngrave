"""ROADMAP 2.18 -- price the stem-side rule by RE-DECIDING one saved record.

PATH: STAGED. ADJUDICATE→EXPORT over a FIXED gather (`review.rerun.rerun`,
the same replay `--control` proves), twice on ONE tree:

  * OFF -- `rhythm._own_stem_side` forced to `(None, None)`, i.e. no head has
    a side and every stroke stays: the pre-2.18 column test. This arm IS the
    control and it can fail: it must reproduce the record's own verdicts N/N
    and write the byte-identical MusicXML, or the probe exits 1.
  * ON  -- the tree as committed.

⚠️ BLIND TO GATHER (`rerun`'s own docstring): 2.18 changes no GATHER row, so
this is the right instrument; a GATHER change would need two re-gathers.

    python3 benchmarks/omr-missing-notes-2026-09/probe/price_stem_side.py \\
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
        "notes_held_out_sum", "bars_with_events", "two_voice_bars")


def arm(record: str, *, off: bool) -> dict:
    real = RH._own_stem_side
    if off:
        RH._own_stem_side = lambda ev: (None, None)
    try:
        d, result, _ing = RR.rerun(record, None, None)
    finally:
        RH._own_stem_side = real
    _xml, rep, ref, _placed = RR.export_with_subjects(result)
    # the BARS the sum held out, by (page, system, staff, cell) -- a count
    # that stays level can hide a swap, a set cannot. ⚠️ From the exporter's
    # own `held` list: the per-subject refusal wrapper attributes a bar's
    # hold-out to the last PARSED subject, which is not the bar.
    held = sorted({f'{b.get("page")}/{b.get("system")}/{b.get("staff")}/'
                   f'{b.get("cell")}'
                   for b in (rep.get("bars_held_out_sum") or {}).get("held")
                   or ()})
    verdicts = RR._verdict_index(result["record"]["verdicts"])
    dur = [v for (q, _s), v in verdicts.items() if q == Q.DURATION]
    return {
        "control_same": d.control_same, "control_differ": d.control_differ,
        "control_absent": d.control_absent, "control_extra": d.control_extra,
        "musicxml_identical": d.musicxml_identical,
        "notes_in_file": d.notes_after,
        "duration_outcomes": dict(collections.Counter(
            f'{v["outcome"]}:{v.get("reason")}' for v in dur)),
        "heads_with_a_far_side_stroke": sum(
            1 for v in dur if (v.get("detail") or {}).get("beams_far_side")),
        "levels_certain": dict(sorted(collections.Counter(
            (v.get("detail") or {}).get("levels_certain")
            for v in dur if "levels_certain" in (v.get("detail") or {})
        ).items())),
        "notes_not_written": rep.get("notes_not_written"),
        "written": {k: (rep.get("written") or {}).get(k) for k in KEYS},
        "bars_held_by_sum": held,
        "changed": [{"subject": c.get("subject"), "quantity":
                     c.get("quantity"), "before": c.get("before"),
                     "after": c.get("after")} for c in d.changed],
        "changed_by_quantity": dict(collections.Counter(
            c.get("quantity") for c in d.changed)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    off = arm(a.record, off=True)
    ok = (off["control_differ"] == 0 and off["control_absent"] == 0
          and off["control_extra"] == 0 and off["musicxml_identical"])
    print("CONTROL (rule OFF reproduces the record): "
          + ("PASSED" if ok else "FAILED"))
    on = arm(a.record, off=False)
    out = {"off": off, "on": on}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    for k in ("duration_outcomes", "heads_with_a_far_side_stroke",
              "levels_certain", "notes_not_written", "written",
              "notes_in_file", "changed_by_quantity"):
        print(f"\n{k}\n  off: {off[k]}\n  on:  {on[k]}")
    a_, b_ = set(off["bars_held_by_sum"]), set(on["bars_held_by_sum"])
    print(f"\nbars held by the sum: off {len(a_)}, on {len(b_)}; newly held "
          f"{sorted(b_ - a_)}; released {sorted(a_ - b_)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
