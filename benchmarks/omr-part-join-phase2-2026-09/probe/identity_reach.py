"""REACH, before anything else: what does the record actually KNOW about identity?

⚠️ This is the first question and not the second. `adjudicate_slot_index`'s own
docstring describes a rule it does not implement -- "a short system pairs by
INSTRUMENT NAME in order of appearance" -- and whether that rule is BUILDABLE
on this document is a reach question, answerable off the record with no arm.

Run:  python3 -m benchmarks.omr-part-join-phase2-2026-09.probe.identity_reach  # (no: plain path)
      python3 benchmarks/omr-part-join-phase2-2026-09/probe/identity_reach.py \
          library/_shared-records/beethoven5-p1-p4.record.json
"""

from __future__ import annotations

import collections
import json
import sys


def main(path: str) -> int:
    d = json.load(open(path))
    rec = d["record"]
    V = rec["verdicts"]
    A = rec["abstentions"]

    def of(name, src):
        return [v for v in src if v["quantity"] == name]

    print("=" * 72)
    print("RECORD:", path)
    print("provenance:", d.get("provenance"))
    print("=" * 72)

    for name in ("staff_ordinal", "system_staff_count", "margin_label",
                 "instrument", "slot_index", "part_partition",
                 "measure_partition"):
        vs = of(name, V)
        ab = of(name, A)
        print("\n--- %-20s verdicts %4d   abstention-rows %4d"
              % (name, len(vs), len(ab)))
        print("    outcomes", dict(collections.Counter(v["outcome"] for v in vs)))
        print("    reasons ", dict(collections.Counter(v.get("reason") for v in vs)))

    print("\n" + "=" * 72)
    print("Q.SLOT_INDEX, per staff  (value, reason)")
    print("=" * 72)
    sl = {v["subject"]: (v["value"], v.get("reason")) for v in of("slot_index", V)}
    for k in sorted(sl):
        print("  %-22s %s" % (k, sl[k]))

    print("\n" + "=" * 72)
    print("Q.PART_PARTITION (document)")
    print("=" * 72)
    for v in of("part_partition", V):
        print(json.dumps({k: v[k] for k in ("subject", "outcome", "value",
                                            "reason")}, indent=1))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1
                  else "library/_shared-records/beethoven5-p1-p4.record.json"))
