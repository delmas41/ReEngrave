"""Does the WIRED run agree with the offline replay, record for record?

Two independent paths to one answer: `price_offline.py` applies the pure rule
to a committed blob, `run_with_stub_roster.py` runs the production wiring with
a stand-in supplier. If they disagree the wiring is not the rule.

Usage:  check_stub_blob.py WIRED.json OFFLINE.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(wired: str, offline: str) -> None:
    w = json.loads(Path(wired).read_text())
    o = json.loads(Path(offline).read_text())
    s = (w.get("contextual") or {}).get("offroster_name_veto")
    if s is None:
        raise SystemExit("REFUSING: the wired blob has no "
                         "`offroster_name_veto` block — the wiring did not run")
    print(f"wired:   {wired}")
    print(f"  work_id={s['work_id']}  roster="
          f"{'present (%d names)' % len(s['roster']) if s['roster'] else None}")
    print(f"  slots={s['slots_vetoed']}  by instrument={s['by_instrument']}  "
          f"records={s['staff_records_vetoed']}")

    wired_keys = {(r["page_index"], r["system_index"], r["staff_index"])
                  for r in s["vetoes"]}
    off_keys = {(r["page_index"], r["system_index"], r["staff_index"])
                for r in o["contextual"]["absent_instrument_veto"]["vetoes"]}
    print(f"offline: {offline}   records={len(off_keys)}")
    print(f"  AGREE on {len(wired_keys & off_keys)} records; "
          f"wired-only {len(wired_keys - off_keys)}, "
          f"offline-only {len(off_keys - wired_keys)}")
    assert wired_keys == off_keys, "the wiring is not the rule"

    # ⚠️ The STAFF-DICT half of the wiring is NOT exercised here, and saying so
    # is the point of this comment. `compose.py` builds its result as
    # `[{"page_index": i, "systems": []}]` and feeds the staves in through
    # `staved=`, so the loop that writes `instrument` / `instrument_veto` onto
    # staff dicts iterates nothing. A count of 0 marked staves below is that
    # fact and NOT evidence about the marker.
    staves = [st for p in w["pages"] for sy in p["systems"]
              for st in sy["staves"]]
    print(f"  staff dicts in this blob: {len(staves)}  "
          "(compose.py supplies none — see the comment; the marker is guarded "
          "by test_offroster_name.TestTheWiring instead)")
    print("  OK")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
