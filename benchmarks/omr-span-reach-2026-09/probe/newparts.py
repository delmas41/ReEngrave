"""Which parts each movement ADDS, per the reference encodings.

⚠️ SELECTION EVIDENCE ONLY. An encoding's part list is a property of the
encoding; the span code reads staves off a printed page.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
rows = {r["work_id"]: r
        for r in json.load(open(ROOT / "benchmarks/omr-span-reach-2026-09/"
                                       "out/inventory.json"))}
for w in sys.argv[1:] or [k for k, r in rows.items() if r["grows"]]:
    r = rows[w]
    print("===", w, r["movement_parts"])
    seen: set[str] = set()
    for k in sorted(r["part_names"], key=int):
        names = r["part_names"][k]
        new = sorted(set(names) - seen)
        print(f"  mvt{k} n={len(names)} NEW={new if seen else '(first)'}")
        seen |= set(names)
