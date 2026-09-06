"""Which pre-finale staves take the Trombone and Tuba slots, and what are they?

The span-reference dump (`out/brahms1/span_reference.txt`) says the pre-finale
span's own reference is placed into the document slot space with its `Timpani`
landing on global slot 8 (`Trombone`) and its first `Violin` on global slot 9
(the score-order prior's `Tuba`). If that is the mechanism, the staves taking
those two slots should be the ones a reduced system puts there — and their OWN
labels, where they carry one, say what they really are.

Nothing here is hand-read: it reports the run's own label evidence for the very
staves it misnames, which is the strongest kind of self-contradiction available
without opening the page.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINALE_FIRST_PAGE = 45


def main() -> None:
    for tag in ("spans-off", "spans-on"):
        blob = json.loads((ROOT / "out" / "brahms1" / f"{tag}.json").read_text()
                          )["contextual"]["absent_instrument_veto"]
        ev = collections.defaultdict(dict)
        for e in blob["label_evidence"]:
            ev[e["page_index"]][e["staff_index"]] = e["instrument"]
        name = {s["slot"]: s["instrument"] for s in blob["slot_instruments"]}
        by_system = collections.defaultdict(list)
        for s in blob["staff_slots"]:
            by_system[(s["page_index"], s["system_index"])].append(s)

        pre = sum(1 for s in blob["staff_slots"]
                  if s["page_index"] < FINALE_FIRST_PAGE)
        own = collections.Counter()
        above = collections.Counter()
        for (p, sy), staves in by_system.items():
            if p >= FINALE_FIRST_PAGE:
                continue
            order = sorted(staves, key=lambda s: s["staff_index"])
            for i, s in enumerate(order):
                if name.get(s["slot"]) not in ("Trombone", "Tuba"):
                    continue
                key = (name[s["slot"]],
                       ev[p].get(s["staff_index"]) or "<no label>")
                own[key] += 1
                a = ev[p].get(order[i - 1]["staff_index"]) if i else None
                above[(name[s["slot"]], a or "<no label>")] += 1

        print(f"===== {tag}: {pre} pre-finale staff records")
        print("  given / its OWN label:")
        for k, n in sorted(own.items(), key=lambda kv: -kv[1]):
            print(f"    {n:4d}  named {k[0]:<9} own label {k[1]}")
        print("  given / the label on the staff ABOVE it:")
        for k, n in sorted(above.items(), key=lambda kv: -kv[1]):
            print(f"    {n:4d}  named {k[0]:<9} above {k[1]}")
        print()


if __name__ == "__main__":
    main()
