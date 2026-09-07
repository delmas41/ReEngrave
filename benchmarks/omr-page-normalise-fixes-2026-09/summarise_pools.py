"""The pooled normalised figure, with the share of it that rests on a JUDGEMENT.

Sean, 2026-09-06: *"down the road I want the truer number to be the one we are
trying to beat, not the higher number."* This prints the candidate for that
number — and beside it the one caveat a headline should never be quoted
without: what fraction of the merged staff-measures were `divisi`, i.e. bars
where two encoded parts genuinely play different notes on one printed staff and
the transform had to CHOOSE between a chord and stacked voices.

`silent_all`, `unison`, `silent_others` and `single` are exact duplication —
the page prints one line and one line is what the derived truth carries, with
nothing decided. `divisi` is the judgement, and `divisi_chorded` /
`divisi_voiced` say which way each one went. They PARTITION `divisi` and are
not summed into the denominator.

⚠️ Reads `controls.json`; measures nothing itself.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/summarise_pools.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIMARY = ("single", "silent_all", "unison", "silent_others", "divisi")


def main() -> int:
    doc = json.loads((HERE / "controls.json").read_text())
    by_id = {r["row_id"]: r for r in doc["rows"]}
    pools = doc.get("pooled") or {}

    print(f"{'pool':40s} {'n':>3s} {'raw NED':>8s} {'raw ed':>7s} "
          f"{'nrm NED':>8s} {'nrm ed':>7s} {'divisi':>7s} {'chorded':>8s}")
    print("-" * 90)
    out = {}
    for name, p in pools.items():
        if name.startswith("_"):
            continue
        census: dict[str, int] = {}
        for rid in p["rows"]:
            for k, v in (by_id[rid]["measure_census"] or {}).items():
                census[k] = census.get(k, 0) + v
        total = sum(census.get(k, 0) for k in PRIMARY) or 1
        divisi = census.get("divisi", 0)
        chorded = census.get("divisi_chorded", 0)
        r, n = p["raw"], p["normalised"]
        out[name] = {
            "n_rows": r["n_rows"],
            "raw_omr_ned": r["omr_ned"], "raw_omr_ed": r["omr_ed"],
            "normalised_omr_ned": n["omr_ned"], "normalised_omr_ed": n["omr_ed"],
            "staff_measures_merged": total,
            "divisi_share": round(divisi / total, 4),
            "divisi_chorded": chorded,
            "divisi_voiced": census.get("divisi_voiced", 0),
            "entire_staff_raw": r["categories"].get(
                "entire staff insert/delete", 0),
            "entire_staff_normalised": n["categories"].get(
                "entire staff insert/delete", 0),
        }
        print(f"{name:40s} {r['n_rows']:>3d} {r['omr_ned']:>8.4f} "
              f"{r['omr_ed']:>7d} {n['omr_ned']:>8.4f} {n['omr_ed']:>7d} "
              f"{divisi / total:>7.4f} {chorded:>8d}")

    (HERE / "pools.json").write_text(json.dumps(
        {"generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/"
                         "summarise_pools.py",
         "warning": doc.get("pooled_warning"),
         "transform_version": doc.get("transform_version"),
         "pools": out}, indent=1) + "\n")
    print("\n⚠️  A NORMALISED POOL IS ITS OWN BENCHMARK ERA. It may not be "
          "differenced against\n    the recorded raw 0.8444 or any historical "
          "figure. The raw→normalised gap is\n    STRUCTURAL CHARGE REMOVED, "
          "not the pipeline improving.")
    print("⚠️  `divisi` is the share of merged staff-measures where the "
          "transform had to CHOOSE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
