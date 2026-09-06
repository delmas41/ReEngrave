"""Per-row: how far is the SCORED truth from the structure of the PRINTED page?

Sean, 2026-09-06: *"The ground truth should be the scan as it is on the page.
An example ... is if the 2 flutes are on one staff on the page and on 2 separate
staves in the MXL."*

This probe answers the structural half, per scan-gate row, from three sources
that are deliberately independent of each other:

  THE FILE   `benchmarks/omr-scan-e2e-2026-09/fixtures/<row>.truth.musicxml` —
             the exact artefact musicdiff scores against. Parsed with
             ElementTree, never a regex, and never via `works.json`'s
             `reference.n_parts` field, which is WRONG for Mahler (it says 38;
             the file carries 25 parts declaring 38 staves).

  THE PAGE   `works.json`'s `staves` list — hand-read off the scan by a human,
             one entry per PRINTED staff of one system, each naming the
             reference part indices that staff carries. `parts: [0, 1]` IS a
             condensed staff. Rows without one abstain and say so.

  OURS       `fixtures/<row><tag>.omr.musicxml` — how many parts we emit.

The output is `structural-divergence.json` plus a table. The number that
matters is `orphan_parts`: reference parts with no printed staff of their own,
i.e. parts musicdiff must charge as `entire staff insert/delete` no matter how
well the page was read.

    python3 benchmarks/omr-headline-validity-2026-09/probe_structural_divergence.py
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"
WORKS = SCAN / "works.json"


def load_rows() -> list[dict]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        for key in ("staves", "condensation"):
            v = row.get(key)
            if isinstance(v, str) and v.startswith("same-as:"):
                row[key] = by_id[v.split(":", 1)[1]][key]
    return rows


def part_list(xml: Path) -> list[dict]:
    """Every <score-part> in a MusicXML file, with its declared staff count.

    A part declaring <staves>2</staves> occupies two printed staves — a grand
    staff — which is the OPPOSITE of condensation and must not be counted as
    one printed staff.
    """
    root = ET.parse(xml).getroot()
    parts = []
    for sp in root.iter("score-part"):
        pid = sp.get("id")
        name_el = sp.find("part-name")
        parts.append({"id": pid,
                      "name": (name_el.text or "").strip() if name_el is not None else ""})
    by_id = {p["id"]: p for p in parts}
    for part in root.iter("part"):
        pid = part.get("id")
        if pid not in by_id:
            continue
        staves = 1
        for st in part.iter("staves"):
            try:
                staves = max(staves, int((st.text or "1").strip()))
            except ValueError:
                pass
        by_id[pid]["declared_staves"] = staves
    for p in parts:
        p.setdefault("declared_staves", 1)
    return parts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="..graft09",
                    help="prediction fixture tag (default: the 20-row baseline's)")
    ap.add_argument("--out", default=str(BENCH / "structural-divergence.json"))
    args = ap.parse_args(argv)

    out_rows = []
    for row in load_rows():
        rid = row["row_id"]
        truth = FIXTURES / f"{rid}.truth.musicxml"
        pred = FIXTURES / f"{rid}{args.tag}.omr.musicxml"
        entry: dict = {
            "row_id": rid,
            "work_id": row["work_id"],
            "pooled": row.get("pooled", True),
            "page": {"printed_staves_on_page": row["page"].get("n_staves"),
                     "n_systems": row["page"].get("n_systems")},
            "works_json_n_parts_field": row["reference"]["n_parts"],
        }
        if truth.is_file():
            tp = part_list(truth)
            entry["truth_file"] = {
                "n_parts": len(tp),
                "n_declared_staves": sum(p["declared_staves"] for p in tp),
                "multi_staff_parts": [p["name"] for p in tp
                                      if p["declared_staves"] > 1],
            }
            entry["field_matches_file"] = (
                len(tp) == row["reference"]["n_parts"])
        else:
            entry["truth_file"] = None
        if pred.is_file():
            entry["ours"] = {"n_parts": len(part_list(pred))}
        else:
            entry["ours"] = None

        staves = row.get("staves")
        if isinstance(staves, list) and entry["truth_file"]:
            n_parts = entry["truth_file"]["n_parts"]
            covered: set[int] = set()
            condensed = []
            for spec in staves:
                idx = list(spec["parts"])
                covered.update(idx)
                if len(idx) > 1:
                    condensed.append({"staff": spec["name"], "parts": idx})
            orphans = sorted(set(range(n_parts)) - covered)
            entry["hand_map"] = {
                "n_printed_staves_one_system": len(staves),
                "n_condensed_staves": len(condensed),
                "condensed": condensed,
                "parts_covered": len(covered),
                "orphan_parts": orphans,
                "n_orphan_parts": len(orphans),
                # the structural surplus: reference parts beyond the number of
                # staves the page prints for them
                "surplus_parts": n_parts - len(staves),
            }
        else:
            entry["hand_map"] = None
            entry["abstain_reason"] = ("no hand-read staves map in works.json"
                                       if not isinstance(staves, list)
                                       else "no trimmed truth on disk")
        out_rows.append(entry)

    doc = {
        "generated_by": "benchmarks/omr-headline-validity-2026-09/"
                        "probe_structural_divergence.py",
        "tag": args.tag,
        "rows": out_rows,
        "summary": {
            "n_rows": len(out_rows),
            "n_with_hand_map": sum(1 for r in out_rows if r["hand_map"]),
            "n_abstained": sum(1 for r in out_rows if not r["hand_map"]),
            "field_disagrees_with_file": [r["row_id"] for r in out_rows
                                          if r.get("field_matches_file") is False],
        },
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    hdr = (f"{'row':40s} {'parts':>6s} {'staves':>7s} {'cond':>5s} "
           f"{'surplus':>8s} {'orphan':>7s} {'ours':>5s}")
    print(hdr)
    print("-" * len(hdr))
    for r in out_rows:
        tf = r["truth_file"] or {}
        hm = r["hand_map"]
        ours = (r["ours"] or {}).get("n_parts", "-")
        if hm:
            print(f"{r['row_id']:40s} {tf.get('n_parts','?'):>6} "
                  f"{hm['n_printed_staves_one_system']:>7} "
                  f"{hm['n_condensed_staves']:>5} {hm['surplus_parts']:>8} "
                  f"{hm['n_orphan_parts']:>7} {ours:>5}")
        else:
            print(f"{r['row_id']:40s} {tf.get('n_parts','?'):>6} "
                  f"{'-':>7} {'-':>5} {'-':>8} {'-':>7} {ours:>5}   "
                  f"ABSTAIN: {r.get('abstain_reason')}")
    print()
    print(f"hand map present on {doc['summary']['n_with_hand_map']} of "
          f"{doc['summary']['n_rows']} rows; "
          f"{doc['summary']['n_abstained']} abstain")
    if doc["summary"]["field_disagrees_with_file"]:
        print("WARN works.json reference.n_parts disagrees with the file on: "
              + ", ".join(doc["summary"]["field_disagrees_with_file"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
