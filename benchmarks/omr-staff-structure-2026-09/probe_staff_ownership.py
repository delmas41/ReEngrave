"""Attribute the scan benchmark's `entire staff insert/delete` bucket.

WHY THIS EXISTS. The vs-industry Addendum 3 measured that our +915 deficit
against Audiveris on the widened 10-row scan pool is ONE bucket: `entire staff
insert/delete`, ours 5,491 against its 2,900 on the five second/third pages,
IDENTICAL (2,676) on the five first pages. The documented suspicion was
`export._stitch_slots` refusing on a staff-count mismatch and falling back to
per-system fragment parts, each pairing with nothing.

This probe tests that, per page, against the artifacts the benchmark already
wrote — the transcription JSON (systems, staves, contextual slot_index) and the
exported MusicXML (the parts musicdiff actually saw) — plus the truth file's
own part list.

Reads only. Writes nothing but stdout / --json.
"""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROWS = [
    "beethoven-sym5-mvt1-984073-p1", "beethoven-sym5-mvt1-984073-p2",
    "beethoven-sym5-mvt1-575951-p1", "beethoven-sym5-mvt1-575951-p2",
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "brahms-sym1-mvt1-317803-p1", "brahms-sym1-mvt1-317803-p2",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
    "bach-brandenburg3-mvt1-468678-p1",
]
SECOND_PAGES = {
    "beethoven-sym5-mvt1-984073-p2", "beethoven-sym5-mvt1-575951-p2",
    "dvorak-sym9-mvt1-405834-p6", "brahms-sym1-mvt1-317803-p2",
    "mahler-sym5-mvt1-local-p3",
}


def part_names(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    return [(sp.findtext("part-name") or "").strip()
            for sp in root.findall(".//score-part")]


def measures_per_part(path: Path) -> list[int]:
    root = ET.parse(path).getroot()
    return [len(p.findall("measure")) for p in root.findall("part")]


def systems_of(result: dict) -> list[dict]:
    return [s for page in result.get("pages", [])
            for s in page.get("systems", []) if s.get("staves")]


def classify(result: dict, n_pred_parts: int) -> tuple[str, dict]:
    """Which structural mechanism this page's parts came out of.

    Mirrors `export._stitch_slots`' own decision so the label is the code's,
    not a guess about it.
    """
    systems = systems_of(result)
    sizes = [len(s["staves"]) for s in systems]
    facts = {"n_systems": len(systems), "system_sizes": sizes}
    if not systems:
        return "no-systems", facts
    if len(systems) == 1:
        return "single-system", facts
    if len(set(sizes)) != 1:
        return "stitch-REFUSED-count-mismatch", facts
    return "stitched", facts


def slot_facts(result: dict) -> dict:
    """What the contextual pass knows — the evidence a slot-aware stitch would use."""
    per_system = []
    for s in systems_of(result):
        per_system.append([st.get("slot_index", -1) for st in s["staves"]])
    assigned = sum(1 for row in per_system for v in row if v is not None and v >= 0)
    total = sum(len(row) for row in per_system)
    union = sorted({v for row in per_system for v in row if v is not None and v >= 0})
    # Would slot-joining actually change the part count? Only if the systems
    # disagree on count (else ordinal already works) AND the slots are a
    # consistent, collision-free labelling.
    collisions = any(len(row) != len(set(row)) for row in per_system)
    return {
        "slots_assigned": assigned, "staves_total": total,
        "distinct_slots": len(union),
        "slot_collision_within_a_system": collisions,
        "per_system_slots": per_system,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=None,
                    help="fixtures dir (default: the main checkout's scan bench)")
    ap.add_argument("--results", default=None, help="composed baseline results json")
    ap.add_argument("--tag", default="restamp-composed")
    ap.add_argument("--audiveris", default=None,
                    help="categories-audiveris-scan11.json, for the side-by-side")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[2]
    fixtures = Path(args.fixtures) if args.fixtures else (
        root / "benchmarks/omr-scan-e2e-2026-09/fixtures")
    results = Path(args.results) if args.results else (
        root / "benchmarks/omr-scan-e2e-2026-09/results-restamp-composed.json")

    ours = {}
    for row in json.loads(results.read_text()).get("rows", []):
        rid = row["row_id"].replace(f".{args.tag}", "")
        cats = row["omr_ned"]["categories"] if isinstance(row.get("omr_ned"), dict) else {}
        ours[rid] = cats
    audi = json.loads(Path(args.audiveris).read_text()) if args.audiveris else {}

    out = []
    for rid in ROWS:
        omr = fixtures / f"{rid}.{args.tag}.omr.json"
        pred = fixtures / f"{rid}.{args.tag}.omr.musicxml"
        truth = fixtures / f"{rid}.truth.musicxml"
        if not (omr.exists() and pred.exists() and truth.exists()):
            out.append({"row": rid, "error": "missing fixture"})
            continue
        result = json.loads(omr.read_text())
        pn, tn = part_names(pred), part_names(truth)
        mech, facts = classify(result, len(pn))
        cats = ours.get(rid, {})
        rec = {
            "row": rid,
            "second_page": rid in SECOND_PAGES,
            "mechanism": mech,
            **facts,
            "pred_parts": len(pn),
            "truth_parts": len(tn),
            "part_deficit": len(tn) - len(pn),
            "pred_measures": sorted(set(measures_per_part(pred))),
            "truth_measures": sorted(set(measures_per_part(truth))),
            "entire_staff_ours": cats.get("entire staff insert/delete", 0),
            "entire_staff_audiveris": audi.get(rid, {}).get(
                "entire staff insert/delete", 0) if audi else None,
            "entire_measure_ours": cats.get("entire measure insert/delete", 0),
            "entire_measure_audiveris": audi.get(rid, {}).get(
                "entire measure insert/delete", 0) if audi else None,
            **slot_facts(result),
        }
        out.append(rec)

    hdr = (f"{'row':<34} {'mechanism':<30} {'sys sizes':<12} "
           f"{'pred':>4} {'truth':>5} {'def':>4} {'ES ours':>8} {'ES audi':>8}")
    print(hdr)
    print("-" * len(hdr))
    for r in out:
        if "error" in r:
            print(f"{r['row']:<34} {r['error']}")
            continue
        print(f"{r['row']:<34} {r['mechanism']:<30} "
              f"{str(r['system_sizes']):<12} {r['pred_parts']:>4} {r['truth_parts']:>5} "
              f"{r['part_deficit']:>4} {r['entire_staff_ours']:>8} "
              f"{r['entire_staff_audiveris'] if r['entire_staff_audiveris'] is not None else '-':>8}")

    # Ownership: group the bucket by mechanism, over the five second pages.
    print("\nOwnership of `entire staff insert/delete`, second/third pages only:")
    by_mech: dict[str, list] = {}
    for r in out:
        if "error" in r or not r["second_page"]:
            continue
        by_mech.setdefault(r["mechanism"], []).append(r)
    tot = sum(r["entire_staff_ours"] for rs in by_mech.values() for r in rs)
    for mech, rs in sorted(by_mech.items(), key=lambda kv: -sum(r["entire_staff_ours"] for r in kv[1])):
        s = sum(r["entire_staff_ours"] for r in rs)
        pct = 100.0 * s / tot if tot else 0.0
        print(f"  {mech:<32} {s:>6} edits  {pct:5.1f}%   rows: "
              f"{', '.join(r['row'] for r in rs)}")
    print(f"  {'TOTAL':<32} {tot:>6}")

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2) + "\n")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
