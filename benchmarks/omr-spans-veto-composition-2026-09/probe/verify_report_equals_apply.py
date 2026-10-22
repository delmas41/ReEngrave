"""`report` and `apply` must produce the SAME veto set and the same slot map.

The 2x2 is derived from two `report` runs: veto-off is the names as assigned,
veto-on is those names minus the vetoed keys. That derivation is only sound if
the vetoed set is not an input to anything upstream of it. Reading
`contextual.py` says it is not -- `vetoed_keys` is consulted where staff dicts
are written and where clefs are corrected, both downstream of `assign_slots` and
`instrument_by_slot` -- but the whole point of this repo's ledger is that
reading the code is not the same as measuring it.

So: run the same pages twice, once `report` and once `apply`, and assert that
the slot map and the veto set are identical. If they are, one `report` run per
spans setting really does carry both veto cells.

Usage:  verify_report_equals_apply.py REPORT.json APPLY.json [...]
"""
from __future__ import annotations

import json
import sys


def load(path):
    b = (json.load(open(path)).get("contextual") or {})[
        "absent_instrument_veto"]
    return (
        b["mode"],
        {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
         for s in b["staff_slots"]},
        {(v["page_index"], v["system_index"], v["staff_index"])
         for v in b["vetoes"]},
        {s["slot"]: (s["instrument"], s["source"])
         for s in b["slot_instruments"]},
    )


def main(pairs):
    ok = True
    for a, b in pairs:
        ma, sa, va, ia = load(a)
        mb, sb, vb, ib = load(b)
        same = (sa == sb, va == vb, ia == ib)
        print(f"{a.split('/')[-1]} ({ma})  vs  {b.split('/')[-1]} ({mb})")
        print(f"  staff->slot identical : {same[0]}  ({len(sa)} records)")
        print(f"  veto set identical    : {same[1]}  ({len(va)} / {len(vb)})")
        print(f"  slot names identical  : {same[2]}  ({len(ia)} slots)")
        if not all(same):
            ok = False
            print("  ⚠️ THE DERIVATION IS UNSOUND — a `report` run does not "
                  "carry the `apply` cell. Re-take the 2x2 with four runs.")
    print()
    print("VERDICT: report == apply" if ok else "VERDICT: REFUSED")
    return 0 if ok else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    raise SystemExit(main(list(zip(args[::2], args[1::2]))))
