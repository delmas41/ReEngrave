"""What does the `speaks for itself` exemption actually spare?

The exemption is borrowed from `absent_instrument.py`, where the name under
veto came FROM a label elsewhere and the staff's own label is CORROBORATION.
Here the name is a DEDUCTION, so the staff's own label is a CONTRADICTION — and
exempting on contradicting evidence is backwards. This prints the labels the
exemption fires on, so that is a reading rather than an argument.

Usage:  exempted_records.py BLOB.json
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def main(path: str) -> None:
    b = (json.loads(Path(path).read_text())
         .get("contextual", {})["absent_instrument_veto"])
    si = {s["slot"]: s for s in b["slot_instruments"]}
    off = {k for k, v in si.items()
           if v["source"] == "score_order" and v["instrument"] == "Tuba"}
    slot_of = {(s["page_index"], s["system_index"], s["staff_index"]):
               s["slot"] for s in b["staff_slots"]}
    ev: dict[int, dict[int, str]] = {}
    for e in b["label_evidence"]:
        ev.setdefault(e["page_index"], {})[e["staff_index"]] = e["instrument"]

    recs = [k for k, s in slot_of.items() if s in off]
    exempt = [k for k in recs if ev.get(k[0], {}).get(k[2]) is not None]
    print(f"{path}")
    print(f"  slot-9 (`Tuba`, score_order) staff records: {len(recs)}")
    print(f"  spared by the exemption: {len(exempt)}")
    print(f"  what those staves' OWN margin says, vs what we export:")
    for name, n in collections.Counter(
            ev[k[0]][k[2]] for k in exempt).most_common():
        print(f"    the page says {name:<10s} -> we export Tuba   x{n}")
    print("\n  the FULL finale systems among them (the graded population):")
    # a full finale system is 16 staves on a page in 45..85
    size = collections.Counter()
    for (p, sy, _st) in slot_of:
        size[(p, sy)] += 1
    for k in sorted(exempt):
        p, sy, st = k
        if 45 <= p <= 85 and size[(p, sy)] == 16:
            print(f"    p{p:02d} sy{sy} staff{st:2d}  page says "
                  f"{ev[p][st]:<10s} truth says Trombone")


if __name__ == "__main__":
    main(sys.argv[1])
