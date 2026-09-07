"""The DOCUMENT reference an arm ended up with, and what each slot is named.

    dump_reference.py ARM.json [ARM.json ...]
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    for path in sys.argv[1:]:
        d = json.load(open(path))
        c = d["contextual"]
        ref = c.get("reference") or []
        blob = c.get("absent_instrument_veto") or {}
        by_slot = {s["slot"]: s["instrument"]
                   for s in blob.get("slot_instruments", [])}
        print(f"\n=== {path}: reference {len(ref)} slots")
        for i, s in enumerate(ref):
            body = s if not isinstance(s, dict) else {
                k: v for k, v in s.items() if k != "staves"}
            print(f"  [{i:2d}] named={by_slot.get(i)!r:22s} {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
