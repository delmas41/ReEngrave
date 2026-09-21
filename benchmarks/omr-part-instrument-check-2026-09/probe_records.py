"""The same question, asked WITHOUT the pipeline — a second route to the same
number.

⚠️ WHY A SECOND INSTRUMENT AT ALL. `check_arm.py` rebuilds a `Log` and runs
the SHIPPED decision, so it measures the code. This reads the committed
record's JSON directly — no `Log`, no `Evidence`, no adjudicator, no scope —
and re-derives the part keys from the subject strings and the slot verdicts
by hand. If the two agree, the shipped check is not agreeing with itself.

⚠️ AND IT ASKS BOTH JOINS ON EVERY DOCUMENT, which the shipped check cannot:
the decision performs the check in the terms of the join it CHOSE, correctly,
so it never reports what the join it REFUSED would have said. That
counterfactual is the interesting half here, and it is a property of a probe
rather than of the pipeline.

    python3 probe_records.py <record.json> [<record.json> ...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _staff(key: str):
    kind, page, system, staff = key.split("/")
    assert kind == "staff", key
    return int(page), int(system), int(staff)


def run(path: str) -> dict:
    rec = json.load(open(path))["record"]
    verdicts = rec["verdicts"]

    partition = next((v for v in verdicts
                      if v["quantity"] == "part_partition"), None)
    names, slots = {}, {}
    for v in verdicts:
        if v["outcome"] != "decided" or v.get("value") is None:
            continue
        if v["quantity"] == "instrument":
            val = v["value"]
            n = val.get("name") if isinstance(val, dict) else val
            if n is not None:
                names[v["subject"]] = n
        elif v["quantity"] == "slot_index":
            slots[v["subject"]] = v["value"]

    print(f"RECORD  {Path(path).name}")
    print(f"JOIN    {partition and partition.get('value')} "
          f"reason={partition and partition.get('reason')}")
    if not names:
        print("DEAD: no staff carries a decided instrument — the check cannot "
              "speak here, and a clean zero would be silence read as "
              "agreement")
        return {"dead": True}
    print(f"REACH   {len(names)} staves named, {len(slots)} slots decided")

    out = {"record": Path(path).name,
           "join": partition and partition.get("value"),
           "reason": partition and partition.get("reason"),
           "staves_named": len(names), "slots_decided": len(slots),
           "joins": {}}

    for label, keyfn in (("ordinal", lambda s: _staff(s)[2]),
                         ("slot", lambda s: slots.get(s))):
        parts = collections.defaultdict(list)
        unkeyed = 0
        for s, n in names.items():
            k = keyfn(s)
            if k is None:
                unkeyed += 1
                continue
            parts[k].append(n)
        contested = {k: sorted(set(v)) for k, v in parts.items()
                     if len(set(v)) > 1}
        multi = sum(1 for v in parts.values() if len(v) > 1)
        chosen = " <- THE JOIN THAT SHIPPED" if (
            partition and (partition.get("value") or {}).get("join") == label
        ) else " (counterfactual — this join was refused)"
        print(f"  [{label}]{chosen}")
        print(f"     parts {len(parts)}, of them {multi} named on two or more "
              f"systems (the only ones that CAN disagree), {unkeyed} staves "
              f"unkeyed")
        print(f"     CONTESTED {len(contested)}")
        for k in sorted(contested, key=str):
            counts = collections.Counter(parts[k])
            print(f"       part {k}: {dict(counts)}")
        out["joins"][label] = {
            "parts": len(parts), "parts_with_two_or_more_named_staves": multi,
            "staves_unkeyed": unkeyed, "parts_contested": len(contested),
            "contested": {str(k): dict(collections.Counter(parts[k]))
                          for k in sorted(contested, key=str)}}
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    results = []
    for p in sys.argv[1:]:
        results.append(run(p))
        print()
    (HERE / "out" / "probe-records.json").write_text(
        json.dumps(results, indent=1))
    return 2 if all(r.get("dead") for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
