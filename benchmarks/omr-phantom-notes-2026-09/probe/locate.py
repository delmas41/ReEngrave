"""Put every lone-pitched bar back on the PRINTED page it came off.

The artefact numbers measures cumulatively WITHIN A PART (the defect
`benchmarks/omr-part-join-phase2-2026-09/` traced to a missing `pdf_path`), so
`P1 m45` and `P9 m45` are not the same instant and neither is a page
coordinate. `system-map-p1-p4.json` is the exporter's OWN system map, asserted
measure-for-measure against the XML when it was built, so it is the one honest
route from a `<measure number=>` back to a printed staff.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from population import ARTEFACT, bars  # noqa: E402

HERE = Path(__file__).resolve().parents[3]
SYSMAP = HERE / "benchmarks/omr-cleanup-count-2026-09/out/system-map-p1-p4.json"


def index(sysmap):
    """(part_id, measure_number) -> the printed staff it was written from."""
    out = {}
    order = []
    for si, s in enumerate(sysmap["systems"]):
        order.append((s["page"], s["system"]))
        for st in s["staves"]:
            for n in range(st["first_measure"], st["last_measure"] + 1):
                out[(st["part_id"], str(n))] = dict(
                    page=s["page"], system=s["system"], sys_ordinal=si,
                    staff=st["staff"], clef=st.get("clef"),
                    fifths=st.get("fifths"),
                    bar_in_system=n - st["first_measure"],
                    n_bars_in_system=st["n_measures"])
    return out, order


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xml", default=str(ARTEFACT))
    ap.add_argument("--sysmap", default=str(SYSMAP))
    ap.add_argument("--json-out")
    args = ap.parse_args()

    sysmap = json.loads(Path(args.sysmap).read_text())
    where, order = index(sysmap)
    rows = bars(args.xml)
    if not where or not rows:
        print("DEAD: no system map or no measures", file=sys.stderr)
        return 2

    placed = sum(1 for r in rows if (r["part"], r["number"]) in where)
    print(f"REACH  measures={len(rows)}  placed on a printed staff={placed}")
    if placed != len(rows):
        print(f"  ⚠️ {len(rows) - placed} measures have no system-map entry")

    lone = [r for r in rows if r["n_notes"] == 1 and r["n_pitched"] == 1]
    under = [r for r in lone
             if r["events"][0]["dur"] is not None and r["barlen"]
             and r["events"][0]["dur"] < r["barlen"]]

    for name, pop in (("ALL lone-pitched", lone), ("UNDERFULL lone-pitched", under)):
        print()
        print(f"=== {name}: {len(pop)}")
        c = collections.Counter()
        for r in pop:
            w = where.get((r["part"], r["number"]))
            if w:
                c[(w["page"], w["system"])] += 1
        for k in order:
            print(f"   page {k[0]} system {k[1]}: {c.get(k, 0)}")

    print()
    print("=== the underfull bars, located")
    recs = []
    for r in sorted(under, key=lambda r: (int(r["part"][1:]), int(r["number"]))):
        w = where.get((r["part"], r["number"]), {})
        e = r["events"][0]
        rec = dict(part=r["part"], measure=r["number"], pitch=e["pitch"],
                   dur=e["dur"], barlen=r["barlen"], type=e["type"], **w)
        recs.append(rec)
        print(f"  {r['part']:>4} m{r['number']:<4} {str(e['pitch']):<4} "
              f"{str(e['type']):<8} dur={e['dur']:<4} | page {w.get('page')} "
              f"sys {w.get('system')} staff {w.get('staff')} "
              f"bar {w.get('bar_in_system')}/{w.get('n_bars_in_system')} "
              f"clef={w.get('clef')}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(recs, indent=1))
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
