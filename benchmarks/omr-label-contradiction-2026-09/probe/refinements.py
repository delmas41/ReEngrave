"""Do any cheap side-signals separate a WRONG EXPORT from a WRONG LABEL?

The contradiction itself says only that the chain (staff -> slot -> name)
disagrees with the page; it does not say which link broke. This asks whether
anything already on the record predicts the direction, against the hand
adjudication in `out/adjudication.json`.

Candidates, all computable from the same summary block:

  duplicate   the exported name is ALREADY carried by another staff of this
              system whose own label agrees with it — an engraver does not name
              one section twice on one system
  read_dup    the READ name is already carried, with agreement, by another
              staff of this system — the mirror
  run         the contradiction has a neighbour: another contradicting staff
              within 2 staff indices in the same system
  family      read and exported names are in the same instrument family
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "benchmarks/omr-label-contradiction-2026-09/out"


def find(pattern: str) -> Path:
    files = subprocess.run(["git", "ls-files", "*.json"], cwd=ROOT,
                           capture_output=True, text=True).stdout.split()
    hits = [f for f in files if pattern in f]
    assert len(hits) == 1, hits
    return ROOT / hits[0]


def rows_with_features(path: Path) -> list[dict]:
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

    out = []
    for (page, system), staves in sorted(by_system.items()):
        agreeing: dict[str, list[int]] = {}
        for r in staves:
            read = ev.get((page, r["staff_index"]))
            exported = slot_name.get(r["slot"])
            if read is not None and read == exported:
                agreeing.setdefault(read, []).append(r["staff_index"])
        bad = []
        for r in staves:
            read = ev.get((page, r["staff_index"]))
            exported = slot_name.get(r["slot"])
            if read is None or exported is None or read == exported:
                continue
            bad.append(r["staff_index"])
        for r in staves:
            read = ev.get((page, r["staff_index"]))
            exported = slot_name.get(r["slot"])
            if read is None or exported is None or read == exported:
                continue
            si = r["staff_index"]
            out.append({
                "page_index": page, "system_index": system, "staff_index": si,
                "slot": r["slot"], "read": read, "exported": exported,
                "source": slot_src.get(r["slot"], "label"),
                "duplicate": bool(agreeing.get(exported)),
                "read_dup": bool(agreeing.get(read)),
                "run": any(o != si and abs(o - si) <= 2 for o in bad),
            })
    return out


def main() -> None:
    adj = json.loads((OUT / "adjudication.json").read_text())
    verdict = {(a["work"], a["page_index"], a["system_index"],
                a["staff_index"]): a["verdict"] for a in adj}
    for work, pattern in (("beet5", "beet5/-fitsearch-spans-on.json"),
                          ("brahms1", "brahms1/-fitsearch-spans-on.json")):
        rows = rows_with_features(find(pattern))
        print(f"== {work}: {len(rows)} contradictions")
        for feat in ("duplicate", "read_dup", "run"):
            tab = Counter()
            for r in rows:
                v = verdict.get((work, r["page_index"], r["system_index"],
                                 r["staff_index"]), "?")
                tab[(bool(r[feat]), v)] += 1
            print(f"   {feat}: " + "  ".join(
                f"{k[0]}/{k[1]}={v}" for k, v in sorted(tab.items(),
                                                       key=lambda x: str(x))))


if __name__ == "__main__":
    main()
