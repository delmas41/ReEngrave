"""The SECOND whole work's residual refusals, in the same shape as the first.

Brahms 1 / Breitkopf, 86 pages, one shared read pass through the composition
harness (`probe/run_brahms.sh`). Chosen because its finale adds trombones that
the earlier movements do not contain — the same shape the veto was built for on
Beethoven 5.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for tag in ("spans-off", "spans-on"):
        blob = json.loads((ROOT / "out" / "brahms1" / f"{tag}.json").read_text()
                          )["contextual"]["absent_instrument_veto"]
        ev = collections.defaultdict(dict)
        for e in blob["label_evidence"]:
            ev[e["page_index"]][e["staff_index"]] = e["instrument"]
        by_system = collections.defaultdict(list)
        for s in blob["staff_slots"]:
            by_system[(s["page_index"], s["system_index"])].append(s)

        print(f"===== {tag}  reference_size={blob['reference_size']}  "
              f"vetoes={len(blob['vetoes'])}")
        if tag == "spans-on":
            print("  slots: " + ", ".join(
                f"{s['slot']}:{s['instrument']}({s['source']})"
                for s in blob["slot_instruments"]))
        att = sorted(p for p, d in ev.items() if "Trombone" in d.values())
        print(f"  Trombone attested on pages: {att}")
        print(f"  by instrument: "
              f"{dict(collections.Counter(v['instrument'] for v in blob['vetoes']))}")
        for v in sorted(blob["vetoes"], key=lambda r: (r["page_index"],
                                                       r["system_index"],
                                                       r["staff_index"])):
            p, sy, st = v["page_index"], v["system_index"], v["staff_index"]
            n = len(by_system[(p, sy)])
            print(f"  p{p:02d} sy{sy} st{st:2d} slot{v['slot']:2d} "
                  f"{v['instrument']:<9} sys_size={n:2d} "
                  f"attested[{v['attested_first']},{v['attested_last']}] "
                  f"outside={v['pages_outside']}")
        print()


if __name__ == "__main__":
    main()
