"""Can bracket-block evidence SEE the Beethoven p.4 mis-join? A bounded probe.

Phase 1 found an ordinal join that SUCCEEDS and is still wrong: on
`beethoven-sym5-mvt1-*-p4` both systems count 11 staves and they are not the
same eleven — system 1 splits `Violoncello` from `Basso` and prints no Timpani,
system 2 prints Timpani and merges the basses, so slots 6-10 are shifted by one
and Violino I's music is grafted onto the Timpani part. Nothing reports it.

Phase 4 step 1 noticed those two rows are the ONLY ones whose blocks read
`brass+string`, which would be block evidence contradicting the slot
assignment — and refused to claim it, because `contextual["reference"]` is
SLOT-indexed while `works.json`'s names are system-1 positions, so on exactly
those rows the comparison is confounded by the mis-join it would be detecting.
That is class 6's own shape appearing in the instrument meant to diagnose
class 6.

This settles it by reading blocks PER SYSTEM instead of per slot.
`Staff.group_index` is set by `system_grouping._assign_groups` from ink-bridging
counts, which are a property of the page raster and are not serialized — so
this re-runs PHASE 1 ONLY (render, binarize, detect staves, assign systems). No
YOLO, no transcription.

⚠️ SCOPE: report whether the block evidence contradicts the slot assignment,
and STOP. Building a fix on it needs a separate number and a separate go-ahead.

⚠️ FIREWALL: `system_grouping.py` is READ and CALLED here, never modified.
`OMR_LEFT_EDGE_SPLIT` and `OMR_CHOIR_GROUPING` are shipped and default-on and
belong to other sessions; this probe leaves them at their defaults.

    python3 benchmarks/omr-structural-parts-2026-09/probe_blocks_per_system.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import lookup  # noqa: E402
from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.system_grouping import assign_systems  # noqa: E402

WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"
ROWS = ["beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"]


def _deref(rows: dict, row: dict, key: str):
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def family_of(name: str) -> str | None:
    m = lookup(name)
    return m.instrument.family if m else None


def pdf_for(row: dict) -> Path | None:
    """The same resolution `scan_eval.py` makes: library_root() / catalog_path."""
    from tools.library.score_library import library_root  # noqa: PLC0415
    cat = (row.get("edition") or {}).get("catalog_path")
    return (library_root() / cat) if cat else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    rows = {r["row_id"]: r for r in json.loads(WORKS.read_text())["rows"]}
    report: dict = {}

    for rid in ROWS:
        row = rows[rid]
        pdf = pdf_for(row)
        print(f"\n=== {rid}\n    pdf: {pdf}")
        if not pdf or not pdf.exists():
            print("    SKIP — page not resolvable on this machine")
            report[rid] = {"error": "pdf not found"}
            continue
        page_index = int((row.get("page") or {})["pdf_page_index"])
        page = render_page(pdf, page_index, dpi=args.dpi)
        pws = detect_staves(page)
        staves, _ = assign_systems(page.binary, list(pws.staves))

        by_system: dict[int, list] = {}
        for st in staves:
            by_system.setdefault(st.system_index, []).append(st)

        sap = _deref(rows, row, "systems_as_printed")
        printed = {i: sap.get(f"system_{i+1}") for i in range(len(by_system))
                   if isinstance(sap, dict)}

        rec = {"systems": []}
        for si, members in sorted(by_system.items()):
            members = sorted(members, key=lambda s: s.line_ys[0])
            groups = [s.group_index for s in members]
            names = [e["name"] for e in (printed.get(si) or [])]
            fams = [family_of(n) for n in names]
            rec["systems"].append({"system": si, "n_staves": len(members),
                                   "groups": groups, "printed": names,
                                   "families": fams})
            print(f"\n    system {si}: {len(members)} staves, "
                  f"{len(set(groups))} blocks  {groups}")
            for k, g in enumerate(groups):
                nm = names[k] if k < len(names) else "?"
                fm = fams[k] if k < len(fams) else "?"
                print(f"      pos {k:>2}  block {g}   {nm:<30} [{fm}]")

        # The question: do the two systems' BLOCK SHAPES differ?
        shapes = [tuple(s["groups"]) for s in rec["systems"]]
        sizes = [[len([g for g in s["groups"] if g == b])
                  for b in sorted(set(s["groups"]))] for s in rec["systems"]]
        rec["block_shapes"] = [list(s) for s in shapes]
        rec["block_sizes"] = sizes
        rec["shapes_differ"] = len(set(shapes)) > 1
        print(f"\n    block sizes per system: {sizes}")
        print(f"    the two systems' block shapes "
              f"{'DIFFER' if rec['shapes_differ'] else 'AGREE'}")
        if rec["shapes_differ"]:
            print("    -> the blocks are position-independent evidence that "
                  "the two systems\n       do NOT hold the same staff "
                  "sequence, which is the mis-join.")
        else:
            print("    -> the blocks CANNOT see the mis-join: they describe "
                  "both systems\n       identically even though the printed "
                  "lineups differ.")
        report[rid] = rec

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = HERE / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
