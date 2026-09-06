"""Print the per-page label evidence and the vetoes a given rule/window fires."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.absent_instrument import find_vetoes            # noqa: E402


def load(path):
    r = json.load(open(path))
    b = (r.get("contextual") or {}).get("absent_instrument_veto")
    if not b:
        raise SystemExit("REFUSING: no report block")
    ev = {}
    for e in b["label_evidence"]:
        ev.setdefault(e["page_index"], {})[e["staff_index"]] = e["instrument"]
    sbs = {(s["page_index"], s["system_index"], s["staff_index"]): s["slot"]
           for s in b["staff_slots"]}
    nm = {s["slot"]: s["instrument"] for s in b["slot_instruments"]}
    src = {s["slot"]: s["source"] for s in b["slot_instruments"]}
    refn = len((r.get("contextual") or {}).get("reference") or [])
    return r, ev, sbs, nm, src, refn


if __name__ == "__main__":
    path = sys.argv[1]
    rule = sys.argv[2] if len(sys.argv) > 2 else "span"
    window = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    r, ev, sbs, nm, src, refn = load(path)
    print(f"=== {Path(path).name}  rule={rule} window={window}")
    for p in sorted(ev):
        print(f"  p{p} labels: {ev[p]}")
    vs = find_vetoes(staff_keys=list(sbs), slot_by_staff=sbs,
                     instrument_name_by_slot=nm, instrument_source=src,
                     evidence=ev, window=window, rule=rule,
                     reference_size=refn)
    print(f"vetoes: {len(vs)}")
    for v in vs:
        print("   ", v)
