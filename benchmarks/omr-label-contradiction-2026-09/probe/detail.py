"""Per-row detail for one artefact, with each contradicting staff's system
context: every staff of that system, its slot, what the reader read there and
what the slot exports. A contradiction is rarely alone — a mis-slotted system
contradicts on several staves at once, and the shape of the whole system is
what an adjudicator needs.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def find(pattern: str) -> Path:
    out = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT,
                         capture_output=True, text=True).stdout.split()
    hits = [p for p in out if pattern in p]
    if len(hits) != 1:
        raise SystemExit(f"{len(hits)} artefacts match {pattern!r}: {hits}")
    return ROOT / hits[0]


def main(argv: list[str]) -> None:
    path = find(argv[0])
    doc = json.loads(path.read_text())
    a = doc["contextual"]["absent_instrument_veto"]
    ev = {(r["page_index"], r["staff_index"]): r["instrument"]
          for r in a["label_evidence"]}
    slot_name = {r["slot"]: r["instrument"] for r in a["slot_instruments"]}
    slot_src = {r["slot"]: r.get("source", "label")
                for r in a["slot_instruments"]}
    by_system: dict[tuple[int, int], list[dict]] = {}
    for r in a["staff_slots"]:
        by_system.setdefault((r["page_index"], r["system_index"]), []).append(r)

    only_pages = {int(x) for x in argv[1:]} if len(argv) > 1 else None
    for (page, system), staves in sorted(by_system.items()):
        rows = []
        bad = 0
        for r in sorted(staves, key=lambda x: x["staff_index"]):
            read = ev.get((page, r["staff_index"]))
            exported = slot_name.get(r["slot"])
            flag = "  <<<" if read and exported and read != exported else ""
            if flag:
                bad += 1
            rows.append(f"    staff {r['staff_index']:2d} slot {r['slot']:3d} "
                        f"read={str(read):16} exported={str(exported):16} "
                        f"src={slot_src.get(r['slot'], '-'):22}{flag}")
        if not bad:
            continue
        if only_pages is not None and page not in only_pages:
            continue
        print(f"page {page} system {system}   ({len(staves)} staves, "
              f"{bad} contradicting)")
        print("\n".join(rows))


if __name__ == "__main__":
    main(sys.argv[1:])
