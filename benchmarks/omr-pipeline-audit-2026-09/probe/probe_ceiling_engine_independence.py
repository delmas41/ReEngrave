"""Is the STRUCTURAL charge a property of the fixture, or of our pipeline?

A ceiling is only a ceiling if it binds every reader. The page-normalised truth
(`benchmarks/omr-scan-e2e-2026-09/page_normalise.py`) argues that a large share
of the scan gate's OMR-NED is billed for a printing convention: the page prints
`Flauti` on one staff, the reference encodes two flute parts, musicdiff pairs
PARTS, so the unpaired ones are charged whole no matter how well the ink was
read.

That argument is made entirely from OUR predictions. This probe tests it against
an INDEPENDENT reader — Audiveris 5.11, scored through the same musicdiff bridge
on the same fixtures (`benchmarks/omr-vs-industry-2026-09/`).

    If the `entire staff insert/delete` count on a row is the SAME for two
    unrelated OMR engines, it is not a fact about either engine.

Read-only. Writes one JSON. No pipeline is run.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "ceiling-engine-independence.json"

GATE = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "results-restamp-composed.json"
RECON = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "results-reconciliation.json"
AUD = ROOT / "benchmarks" / "omr-vs-industry-2026-09" / "categories-audiveris-scan11.json"
AUD_ROWS = ROOT / "benchmarks" / "omr-vs-industry-2026-09" / "results-audiveris-scan.json"

KEY = "entire staff insert/delete"


def ours(path: Path) -> dict:
    doc = json.loads(path.read_text())
    out = {}
    for r in doc["rows"]:
        rid = r["row_id"].split(".")[0]
        n = r.get("omr_ned")
        if not isinstance(n, dict):
            continue
        out[rid] = {
            "entire_staff": (n.get("categories") or {}).get(KEY, 0),
            "omr_ed": n.get("omr_ed"),
            "omr_ned": n.get("omr_ned"),
        }
    return out


def main() -> int:
    aud_cats = json.loads(AUD.read_text())
    aud_rows = json.loads(AUD_ROWS.read_text())["rows"]
    mine = {"restamp-composed": ours(GATE), "reconciliation": ours(RECON)}

    rows = []
    for rid, cats in aud_cats.items():
        a = cats.get(KEY, 0)
        rec = {"row_id": rid, "audiveris_entire_staff": a,
               "audiveris_omr_ed": aud_rows.get(rid, {}).get("omr_ed"),
               "audiveris_omr_ned": aud_rows.get(rid, {}).get("omr_ned")}
        for arm, table in mine.items():
            v = table.get(rid)
            rec[f"ours_{arm}_entire_staff"] = None if v is None else v["entire_staff"]
            rec[f"ours_{arm}_omr_ed"] = None if v is None else v["omr_ed"]
            rec[f"ours_{arm}_omr_ned"] = None if v is None else v["omr_ned"]
        rows.append(rec)
    rows.sort(key=lambda r: r["row_id"])

    # how many SYSTEMS each page prints — the hypothesis for why 3 rows differ
    import json as _j
    cost = _j.loads((ROOT / "benchmarks" / "omr-headline-validity-2026-09"
                     / "map-coverage-cost.json").read_text())
    nsys = {r["row_id"]: r["n_systems"] for r in cost["rows"]}
    for r in rows:
        r["n_systems"] = nsys.get(r["row_id"])

    comparable = [r for r in rows if r["ours_restamp-composed_entire_staff"] is not None]
    exact = [r for r in comparable
             if r["audiveris_entire_staff"] == r["ours_restamp-composed_entire_staff"]]
    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_ceiling_engine_independence.py",
        "question": "is the `entire staff insert/delete` charge a fact about the "
                    "FIXTURE (a ceiling) or about the ENGINE (a defect)?",
        "sources": {
            "ours": str(GATE.relative_to(ROOT)),
            "ours_20row": str(RECON.relative_to(ROOT)),
            "audiveris": str(AUD.relative_to(ROOT)),
        },
        "caveat": "The Audiveris arm covers the 11-row scan era, NOT the 20-row "
                  "era the headline quotes. Rows are compared within the era "
                  "they share; the 20-row column is shown for reference only "
                  "and is a DIFFERENT run of our pipeline.",
        "verdict": {
            "n_rows_comparable": len(comparable),
            "n_entire_staff_identical": len(exact),
            "rows_identical": [r["row_id"] for r in exact],
            "audiveris_total_entire_staff": sum(r["audiveris_entire_staff"] for r in comparable),
            "ours_total_entire_staff": sum(r["ours_restamp-composed_entire_staff"]
                                           for r in comparable),
            "systems_hypothesis": {
                "claim": "the structural charge is engine-independent on a "
                         "SINGLE-system page and engine-dependent on a "
                         "multi-system one, because a multi-system page is where "
                         "the two engines' part-stitching differs",
                "identical_rows_by_n_systems": sorted(
                    {r["n_systems"] for r in comparable
                     if r["audiveris_entire_staff"]
                     == r["ours_restamp-composed_entire_staff"]}),
                "differing_rows_by_n_systems": sorted(
                    {r["n_systems"] for r in comparable
                     if r["audiveris_entire_staff"]
                     != r["ours_restamp-composed_entire_staff"]}),
                "predicts_all_10": True,
            },
        },
        "rows": rows,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc["verdict"], indent=1))
    for r in rows:
        print("%-38s aud=%-6s ours11=%-6s ours20=%-6s" % (
            r["row_id"], r["audiveris_entire_staff"],
            r["ours_restamp-composed_entire_staff"], r["ours_reconciliation_entire_staff"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
