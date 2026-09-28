#!/usr/bin/env python3
"""ROADMAP 2.11b — base vs arm on ONE document, against the roadmap's own
gate: 0 other READ clefs changed.

    python3 benchmarks/omr-clef-geometry-2026-09/probe/compare_offstaff.py \
        --base <out>/base-litolff.record.json \
        --arm  <out>/arm-litolff.record.json \
        --name litolff

A READ clef is a DECIDED verdict (a value, not merely a candidate set). This
prints, per document:

  * every subject whose clef verdict's OUTCOME or VALUE differs base->arm;
  * of those, how many were READ (DECIDED) in the base and changed VALUE
    (the gate) vs. ABSTAINED/NARROWED in the base and newly DECIDED in the
    arm (the intended effect: an off-staff box that was a staff's only
    witness now abstains at ADJUDICATE and 2.10's own gap machinery, already
    running in both arms, fills it downstream);
  * the `clef_box_off_the_staff` discounts the arm recorded, by subject.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.omr.staged.record_io import load_record          # noqa: E402
from tools.omr.staged.adjudicators import clef as C          # noqa: E402


def _clef_verdicts(path: str) -> Dict[str, dict]:
    data = load_record(path)
    rec = data["record"]
    out = {}
    for v in rec["verdicts"]:
        if v["quantity"] == "clef":
            out[v["subject"]] = v
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-json")
    a = ap.parse_args()

    base = _clef_verdicts(a.base)
    arm = _clef_verdicts(a.arm)

    changed = []
    read_changed = []
    newly_filled = []
    for subj in sorted(set(base) | set(arm)):
        b, r = base.get(subj), arm.get(subj)
        b_outcome = b["outcome"] if b else None
        r_outcome = r["outcome"] if r else None
        b_value = b.get("value") if b else None
        r_value = r.get("value") if r else None
        if b_outcome == r_outcome and b_value == r_value:
            continue
        row = {"subject": subj,
               "base": {"outcome": b_outcome, "value": b_value,
                        "reason": b.get("reason") if b else None,
                        "decider": b.get("decider") if b else None},
               "arm": {"outcome": r_outcome, "value": r_value,
                       "reason": r.get("reason") if r else None,
                       "decider": r.get("decider") if r else None}}
        changed.append(row)
        if b_outcome == "decided" and r_outcome == "decided" and b_value != r_value:
            read_changed.append(row)
        elif b_outcome != "decided" and r_outcome == "decided":
            newly_filled.append(row)

    discounted = []
    for subj, v in arm.items():
        entries = (v.get("detail") or {}).get(C.OFF_STAFF_REASON)
        if entries:
            discounted.append({"subject": subj, "discounted": entries})

    print(f"== {a.name} ==")
    print(f"clef verdicts: base={len(base)} arm={len(arm)}")
    print(f"TOTAL changed (outcome or value): {len(changed)}")
    print(f"READ CLEFS CHANGED (DECIDED->DECIDED, different value) "
          f"[GATE: must be 0]: {len(read_changed)}")
    for row in read_changed:
        print(f"   {row['subject']}: base={row['base']['value']} "
              f"({row['base']['decider']}/{row['base']['reason']}) -> "
              f"arm={row['arm']['value']} "
              f"({row['arm']['decider']}/{row['arm']['reason']})")
    print(f"newly DECIDED in the arm (was not DECIDED in base): "
          f"{len(newly_filled)}")
    for row in newly_filled:
        print(f"   {row['subject']}: base={row['base']['outcome']}"
              f"/{row['base']['value']} -> "
              f"arm={row['arm']['value']} ({row['arm']['decider']}/"
              f"{row['arm']['reason']})")
    print(f"clef verdicts carrying a clef_box_off_the_staff discount in "
          f"the arm: {len(discounted)}")
    for row in discounted:
        print(f"   {row['subject']}: {row['discounted']}")

    out = {"name": a.name, "n_base": len(base), "n_arm": len(arm),
           "changed": changed, "read_clefs_changed": read_changed,
           "newly_filled": newly_filled, "discounted": discounted}
    if a.out_json:
        Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out_json).write_text(json.dumps(out, indent=2))
        print("wrote", a.out_json)
    return 0 if not read_changed else 1


if __name__ == "__main__":
    raise SystemExit(main())
