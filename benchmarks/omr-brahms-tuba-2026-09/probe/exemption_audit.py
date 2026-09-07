"""Why do only 15 of the 102 slot-9 staff records get vetoed?

The `speaks for itself` exemption keys on `(page_index, staff_index)` — the
frame `absent_instrument.label_evidence` uses — and a staff INDEX is numbered
across the PAGE, not per system. So on a page whose second system's staves
continue the count, a labelled staff of system 0 can share an index with a
slot-9 staff of system 1, and vice versa. This measures whether that is what is
happening and how many records it reaches.

Usage:  exemption_audit.py BLOB.json
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
    tuba = {k for k, v in si.items() if v["instrument"] == "Tuba"}
    slot_of = {(s["page_index"], s["system_index"], s["staff_index"]):
               s["slot"] for s in b["staff_slots"]}
    ev: dict[int, dict[int, str]] = {}
    for e in b["label_evidence"]:
        ev.setdefault(e["page_index"], {})[e["staff_index"]] = e["instrument"]

    recs = [k for k, s in slot_of.items() if s in tuba]
    exempt = [k for k in recs if ev.get(k[0], {}).get(k[2]) is not None]
    print(f"{path}\n  slot-9 staff records: {len(recs)}   "
          f"exempt by `speaks for itself`: {len(exempt)}")
    what = collections.Counter(ev[k[0]][k[2]] for k in exempt)
    print(f"  the label the exemption fired on: {dict(what)}")

    # Is the exempting label on a staff of the SAME system, or a different one?
    same = other = 0
    for k in exempt:
        p, sy, st = k
        # every staff record on this page that carries this index
        holders = [key for key in slot_of if key[0] == p and key[2] == st]
        if any(key[1] != sy for key in holders):
            other += 1
        else:
            same += 1
    print(f"  exempting label sits on THIS system's own staff index: {same}")
    print(f"  ... on a staff index shared with ANOTHER system: {other}")

    # How many pages in this run carry more than one system?
    per_page = collections.defaultdict(set)
    for (p, sy, _st) in slot_of:
        per_page[p].add(sy)
    multi = sum(1 for p, s in per_page.items() if len(s) > 1)
    print(f"  pages with >1 system: {multi} of {len(per_page)}")
    # And does staff_index restart per system on this document?
    restarts = 0
    for p, systems in per_page.items():
        if len(systems) < 2:
            continue
        idx = collections.defaultdict(list)
        for (pp, sy, st) in slot_of:
            if pp == p:
                idx[sy].append(st)
        mins = [min(v) for _k, v in sorted(idx.items())]
        if len(set(mins)) == 1:
            restarts += 1
    print(f"  ... of which staff_index RESTARTS at 0 per system: {restarts}")


if __name__ == "__main__":
    main(sys.argv[1])
