"""Price the block-shape mis-join detector: its FALSE POSITIVE rate on 20 rows.

`probe_blocks_per_system.py` showed that on `beethoven-sym5-mvt1-*-p4` the two
systems count 11 staves each and their bracket blocks have DIFFERENT SHAPES
([4,2,5] vs [4,3,4]) — position-independent evidence that they do not hold the
same staff sequence, which is the mis-join. That is 2 true positives.

The number that governs whether a consumer is worth building is the other one:
**how many rows show disagreeing block shapes where the join is CORRECT.** A
detector that flags the two bad rows and nothing else is worth building. One
that also flags correct joins is a refusal machine — and a refusal is not free,
because `_stitch_slots` then falls back to per-system fragments, which Phase 1
measured as costing more `entire measure` than the stitched parts do.

⚠️ Block boundary RECALL is 0.523 on this corpus and is NOT evenly distributed
(brahms p4 emits one block for all 14 staves). A row whose blocks are
under-detected in ONE system and not the other will show a shape difference
that means nothing at all. That is the false-positive mechanism to look for,
and it is why this is measured rather than assumed.

THE POPULATION is the multi-system rows where the ORDINAL JOIN SUCCEEDS —
where counts differ, `_stitch_slots` already refuses and a detector is moot.

GROUND TRUTH from `works.json`: a row carrying one `staves` lineup asserts the
page has a single hand-verified lineup, so its join is correct; a row carrying
`systems_as_printed` with differing per-system lineups has a wrong join.

⚠️ SCOPE: report the rate. Do NOT build the consumer, do NOT touch
`contextual.py`.

⚠️ FIREWALL: `system_grouping.py` is read and called, never modified;
`OMR_LEFT_EDGE_SPLIT` / `OMR_CHOIR_GROUPING` stay at their shipped defaults.

    python3 benchmarks/omr-structural-parts-2026-09/probe_shape_false_positives.py --json shape-fp.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[0]
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.preprocessing import render_page  # noqa: E402
from tools.omr.staff_detector import detect_staves  # noqa: E402
from tools.omr.system_grouping import assign_systems  # noqa: E402

WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"


def _deref(rows: dict, row: dict, key: str):
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def join_is_wrong(rows: dict, rid: str) -> bool | None:
    """True/False from the hand-verified map; None where it cannot say."""
    row = rows[rid]
    if isinstance(_deref(rows, row, "staves"), list):
        return False          # one lineup asserted for the whole page
    sap = _deref(rows, row, "systems_as_printed")
    if isinstance(sap, dict):
        lineups = [tuple(e["name"] for e in v) for k, v in sorted(sap.items())
                   if k.startswith("system_") and isinstance(v, list)]
        if len(lineups) >= 2:
            return len(set(lineups)) > 1
    return None


def pdf_for(row: dict) -> Path | None:
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

    print(f"{'row':<34} {'sizes':>10} {'block shapes':>26} {'shapes':>9} "
          f"{'join':>9} {'verdict':>8}")
    for rid in sorted(rows):
        row = rows[rid]
        pdf = pdf_for(row)
        page_index = (row.get("page") or {}).get("pdf_page_index")
        if not pdf or not pdf.exists() or page_index is None:
            report[rid] = {"skip": "page not resolvable"}
            print(f"{rid:<34} {'— page not resolvable':>10}")
            continue
        page = render_page(pdf, int(page_index), dpi=args.dpi)
        pws = detect_staves(page)
        staves, _ = assign_systems(page.binary, list(pws.staves))

        by_system: dict[int, list] = {}
        for st in staves:
            by_system.setdefault(st.system_index, []).append(st)
        if len(by_system) < 2:
            report[rid] = {"skip": "single system", "n_systems": 1}
            print(f"{rid:<34} {'— single system':>10}")
            continue

        counts, shapes = [], []
        for si in sorted(by_system):
            members = sorted(by_system[si], key=lambda s: s.line_ys[0])
            groups = [s.group_index for s in members]
            counts.append(len(members))
            shapes.append(tuple(len([g for g in groups if g == b])
                                for b in sorted(set(groups))))

        ordinal_ok = len(set(counts)) == 1     # the join _stitch_slots makes
        differ = len(set(shapes)) > 1
        wrong = join_is_wrong(rows, rid)

        verdict = "—"
        if not ordinal_ok:
            verdict = "moot"                   # the join already refuses
        elif wrong is None:
            verdict = "no truth"
        elif differ and wrong:
            verdict = "TP"
        elif differ and not wrong:
            verdict = "FP"
        elif not differ and wrong:
            verdict = "FN"
        else:
            verdict = "TN"

        report[rid] = {"staff_counts": counts,
                       "block_shapes": [list(s) for s in shapes],
                       "ordinal_join_succeeds": ordinal_ok,
                       "shapes_differ": differ, "join_is_wrong": wrong,
                       "verdict": verdict}
        print(f"{rid:<34} {str(counts):>10} "
              f"{str([list(s) for s in shapes]):>26} "
              f"{('DIFFER' if differ else 'agree'):>9} "
              f"{('WRONG' if wrong else 'ok' if wrong is not None else '?'):>9} "
              f"{verdict:>8}")

    tally: dict[str, list[str]] = {}
    for rid, rec in report.items():
        v = rec.get("verdict")
        if v in {"TP", "FP", "FN", "TN"}:
            tally.setdefault(v, []).append(rid)

    print("\nAmong rows where the ordinal join SUCCEEDS (the only population "
          "a detector could act on):\n")
    for v, label in (("TP", "shapes differ, join IS wrong   (true positive)"),
                     ("FP", "shapes differ, join is correct (FALSE POSITIVE)"),
                     ("FN", "shapes agree, join IS wrong    (miss)"),
                     ("TN", "shapes agree, join is correct  (true negative)")):
        got = tally.get(v, [])
        print(f"  {label:<48} {len(got)}")
        for r in got:
            print(f"      {r}")
    fp, tp = len(tally.get("FP", [])), len(tally.get("TP", []))
    n = fp + tp + len(tally.get("FN", [])) + len(tally.get("TN", []))
    print(f"\nfalse-positive rate: {fp}/{n} rows judged"
          + (f"   precision {tp}/{tp+fp}" if tp + fp else ""))

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = HERE / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
