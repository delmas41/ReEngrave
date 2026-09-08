"""Step 4 — separate the causes behind `entire staff` / no part correspondence.

⚠️ **THE POINT OF THIS FILE IS THAT THE BUCKET IS A MIXTURE.** The handoff
files three causes under one name; any structural fix priced against the bucket
is priced against all of them at once. This classifies every scan-gate row
whose part join fails, from evidence already on disk, and reports the symbol
mass each cause owns.

THE CLASSIFIER IS DERIVED, not hand-assigned. Three facts, all hand-verified
and all already in `benchmarks/omr-scan-e2e-2026-09/works.json`:

  * `page.n_systems`    — how many systems the page prints
  * `page.n_staves`     — how many FIVE-LINE staves it prints, summed over
                          systems (so a 2-system page of 11 reads 22)
  * `len(staves)`       — the hand-verified lineup: one entry per PRINTED
                          staff, INCLUDING one-line percussion rules

and one from the prediction: how many `<part>` elements we emitted.

    pred == n_staves and n_systems > 1   ->  A_stitch_refused
                                             (one part per system-staff: the
                                             documented `_stitch_slots` refusal)
    map == 0                             ->  D_no_lineup   (a missing input)
    map  > pred                          ->  B_undetectable_staves
                                             (the lineup names staves the
                                             five-line detector cannot find)
    map  < pred                          ->  C_lineup_arity
                                             (one lineup entry covers several
                                             printed staves)

⚠️ B and C are the INSTRUMENT's arity gate, not a reading fault. A is the
pipeline. D is an absent hand-verified fact. Only A is a structural defect of
the reader, and it already has a measured fix (`OMR_SLOT_STITCH`).

Run:
    python3 benchmarks/omr-part-join-2026-09/separate_causes.py \
        --ledger benchmarks/omr-symbol-ledger-2026-09/out/ledger-summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"

CAUSES = {
    "A_stitch_refused": "_stitch_slots refuses; we emit one part per system-staff",
    "B_undetectable_staves": "the lineup names staves the five-line detector cannot find",
    "C_lineup_arity": "one lineup entry covers several printed staves",
    "D_no_lineup": "no hand-verified staff map on this row",
}


def staves_of(row, rows):
    st = row.get("staves")
    seen = set()
    while isinstance(st, str) and st.startswith("same-as:"):
        other = st.split(":", 1)[1].strip()
        if other in seen:
            return None
        seen.add(other)
        st = (rows.get(other) or {}).get("staves")
    return st if isinstance(st, list) else None


def classify(n_map, n_pred, n_staves, n_systems):
    if n_pred == n_staves and (n_systems or 1) > 1:
        return "A_stitch_refused"
    if n_map == 0:
        return "D_no_lineup"
    if n_map > n_pred:
        return "B_undetectable_staves"
    if n_map < n_pred:
        return "C_lineup_arity"
    return "unexplained"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True,
                    help="a run_ledger.py ledger-summary.json")
    a = ap.parse_args()

    works = json.loads(WORKS.read_text())
    wrows = {r["row_id"]: r for r in works["rows"]}
    led = json.loads(Path(a.ledger).read_text())

    table = []
    mass = Counter()
    rows_per = Counter()
    for s in led["rows"]:
        rid = s["row_id"]
        w = wrows.get(rid, {})
        page = w.get("page", {})
        st = staves_of(w, wrows)
        n_map = len(st) if st else 0
        info = s["part_join_info"]
        n_pred = info["n_pred_parts"]
        n_staves = page.get("n_staves")
        n_sys = page.get("n_systems")
        resolved = info.get("status") == "resolved"
        unc = s["outcomes"].get("uncorresponded", 0)
        total = sum(s["outcomes"].values())
        cause = "-" if resolved else classify(n_map, n_pred, n_staves, n_sys)
        if not resolved:
            mass[cause] += unc
            rows_per[cause] += 1
        table.append(dict(row_id=rid, resolved=resolved, cause=cause,
                          n_map=n_map, n_pred=n_pred, n_staves=n_staves,
                          n_systems=n_sys, uncorresponded=unc, rows=total))

    w1 = max(len(t["row_id"]) for t in table)
    print(f"{'row_id':{w1}} {'sys':>3} {'staves':>6} {'map':>4} {'pred':>4} "
          f"{'rows':>5} {'uncorr':>6}  cause")
    for t in table:
        print(f"{t['row_id']:{w1}} {str(t['n_systems']):>3} "
              f"{str(t['n_staves']):>6} {t['n_map']:>4} {t['n_pred']:>4} "
              f"{t['rows']:>5} {t['uncorresponded']:>6}  {t['cause']}")

    print("\n" + "=" * 72)
    print("THE BUCKET, SEPARATED")
    print("=" * 72)
    tot_unc = sum(mass.values())
    for c, n in mass.most_common():
        print(f"  {c:<24} {rows_per[c]:>2} rows  {n:>6} symbol rows "
              f"{n/max(tot_unc,1):6.1%}   {CAUSES.get(c,'?')}")
    print(f"  {'TOTAL':<24} {sum(rows_per.values()):>2} rows  {tot_unc:>6}")

    # ---- CONTROLS. A printed zero here is a suspect, so both are positive. --
    pooled_pu = (led["pooled"]["uncorresponded_reasons"].get("part_unresolved", 0))
    n_resolved = sum(1 for t in table if t["resolved"])
    print("\nCONTROLS")
    print(f"  causes sum to the pooled part_unresolved mass: "
          f"{tot_unc} vs {pooled_pu}  "
          f"{'OK' if tot_unc == pooled_pu else 'MISMATCH'}")
    print(f"  rows classified 'unexplained': "
          f"{rows_per.get('unexplained', 0)}  (positive control: "
          f"{sum(rows_per.values())} rows were classified at all)")
    print(f"  rows whose join RESOLVED and are therefore not in the table above: "
          f"{n_resolved} of {len(table)}")

    out = Path(__file__).resolve().parent / "causes.json"
    out.write_text(json.dumps(
        {"rows": table, "mass": dict(mass), "rows_per_cause": dict(rows_per),
         "pooled_part_unresolved": pooled_pu, "ledger": str(a.ledger)}, indent=1))
    print(f"\nwrote {out}")
    return 0 if tot_unc == pooled_pu and not rows_per.get("unexplained") else 1


if __name__ == "__main__":
    raise SystemExit(main())
