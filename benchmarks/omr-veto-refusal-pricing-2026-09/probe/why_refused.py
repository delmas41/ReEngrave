"""Per refusal: which anchor arithmetic failed, and by how much.

`absent_instrument._anchored_keys` exempts a staff whose neighbours leave it no
freedom — the slots between the nearest known slot above and the nearest known
slot below must number exactly the staves between them. The veto's docstring
says the finale's strings are kept by the SYSTEM'S OWN END acting as the lower
anchor. Eighteen finale string staves are refused anyway, so for each one this
prints the two anchors and the two counts that failed to match: the deficit is
how many slots the system skipped below the staff, i.e. how many parts the page
suppressed (or the detector missed) beneath it.

Reads the composition harness's own spans-on report blob. No pipeline run.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

ROOT = Path(__file__).resolve().parents[1]
BLOB = (Path("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "agent-abe066cff5c6c7283/benchmarks/"
             "omr-spans-veto-composition-2026-09/out/whole-spans-on.json"))


def main() -> None:
    blob = json.loads(BLOB.read_text())["contextual"]["absent_instrument_veto"]
    ref_size = blob["reference_size"]
    name_by_slot = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
    slot_by_staff = {(s["page_index"], s["system_index"], s["staff_index"]):
                     s["slot"] for s in blob["staff_slots"]}
    ev = defaultdict(dict)
    for e in blob["label_evidence"]:
        ev[e["page_index"]][e["staff_index"]] = e["instrument"]
    by_system = defaultdict(list)
    for (p, sy, st) in slot_by_staff:
        by_system[(p, sy)].append(st)

    print(f"reference_size = {ref_size}  rule={blob['rule']} "
          f"window={blob['window']}")
    for v in sorted(blob["vetoes"], key=lambda r: (r["page_index"],
                                                   r["system_index"],
                                                   r["staff_index"])):
        p, sy, st = v["page_index"], v["system_index"], v["staff_index"]
        order = sorted(by_system[(p, sy)])
        pos = order.index(st)
        anchors = [(-1, -1)]
        for i, si in enumerate(order):
            if si in ev[p]:
                slot = slot_by_staff.get((p, sy, si))
                if slot is not None and slot >= 0:
                    anchors.append((i, slot))
        anchors.append((len(order), ref_size))
        above = [a for a in anchors if a[0] < pos][-1]
        below = [a for a in anchors if a[0] > pos][0]
        (j, sa), (k, sb) = above, below
        print(f"p{p:02d} sy{sy} st{st:2d} slot{v['slot']:2d} "
              f"{v['instrument']:<10} system_size={len(order):2d} "
              f"anchor_above=(pos {j}, slot {sa}) "
              f"anchor_below=(pos {k}, slot {sb}) "
              f"slots={sb - sa} staves={k - j} "
              f"deficit={(sb - sa) - (k - j)}")


if __name__ == "__main__":
    main()
