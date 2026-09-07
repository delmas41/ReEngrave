"""Prototype the "% of achievable" scale on real committed numbers.

Sean, 2026-09-07: one unit, 0-100, higher is better, on every row — because
today 1.000 means "perfect" in one table and "catastrophic" in the next.

    error metric  (lower better, natural worst W):  pct = 100 * (W - M) / (W - F)
    rate  metric  (higher better, natural best 1):  pct = 100 * V / C

`F` is the achievable FLOOR of an error metric and `C` the achievable CEILING of
a rate. Both are only admissible if derived from an artefact INDEPENDENT of our
own output (a truth file, a render, an external engine) — otherwise the pipeline
grades itself against its own limitations and scores 100 by standing still.

⚠️ THE ASSUMPTION DIRECTION RULE. Where a ceiling is unknown it is assumed at
the value that makes the score as LOW as it can legitimately be — F = 0 for an
error metric, C = 1 for a rate — so a missing ceiling can never manufacture a
high number. Such a row is stamped `ceiling_kind: "assumed"` and is not poolable
with measured ones.

Read-only over committed artefacts. Runs no pipeline and scores no XML.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "pct-of-achievable-prototype.json"

# ⚠️ SUPERSEDED EVIDENCE, 2026-09-07. The first cut of this probe read
# `benchmarks/omr-headline-validity-2026-09/results-normalised-arm.json`
# (transform 1.1.0, the `..graft09` arm, 11 rows, 8 normalised). That artefact
# is NOT on the arm the headline quotes: nine of its eleven rows disagree with
# `results-reconciliation.json`, one of them (Bach) by 572 edits. The
# page_normalise fixes landed the same night and produced a 20-row arm on the
# `.reconciliation` tag whose `pooled_raw_over_all_scored_rows.omr_ned` is
# EXACTLY the canonical 0.8443958865999122 — so the ceiling and the headline now
# share an arm, which is the condition this whole design rests on.
NORM = ROOT / "benchmarks" / "omr-page-normalise-fixes-2026-09" / "results-normalised-arm-20row.json"
NORM_SUPERSEDED = ROOT / "benchmarks" / "omr-headline-validity-2026-09" / "results-normalised-arm.json"
INDEP = HERE / "ceiling-engine-independence.json"
READING = ROOT / "benchmarks" / "omr-reading-vs-reproduction-2026-09" / "results.json"
RECORD = ROOT / "benchmarks" / "omr-ned-2026-08" / "current-accuracy.json"
RECON = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "results-reconciliation.json"

# OMR-NED's natural worst case: predict nothing. ed = truth_symbols,
# denominator = truth_symbols + 0, so the ratio is exactly 1.
W = 1.0


def pct_error(m: float, floor: float) -> float:
    return 100.0 * (W - m) / (W - floor)


def pct_rate(v: float, ceiling: float) -> float:
    return 100.0 * v / ceiling


def main() -> int:
    norm = json.loads(NORM.read_text())
    indep = json.loads(INDEP.read_text())
    corroborated = set(indep["verdict"]["rows_identical"])
    es_by_row = {r["row_id"]: r["audiveris_entire_staff"] for r in indep["rows"]}

    scan_rows = []
    for r in norm["rows"]:
        rid = r["row_id"]
        raw, nz = r["raw"], r.get("norm") or {}
        row = {
            "row_id": rid,
            "family": "scan",
            "raw_omr_ned": raw["omr_ned"],
            "raw_omr_ed": raw["omr_ed"],
            "truth_symbols_raw": raw["truth_symbols"],
            "pred_symbols": raw["pred_symbols"],
        }
        if not r.get("normalised"):
            row.update({
                "scoreable": False,
                "tier": None,
                "why": "no hand-read staves map, so no page-normalised truth",
                "ceiling_kind": None,
                "pct_of_achievable": None,
            })
            scan_rows.append(row)
            continue
        t_norm = nz["truth_symbols"]
        denom = raw["truth_symbols"] + t_norm      # a perfect page-faithful reader
        # THE FLOOR ESTIMATOR, stated explicitly. The floor must be a charge no
        # measured reader has avoided, so it is the MINIMUM `entire staff` count
        # over every engine scored on this row — ours, and Audiveris where the
        # industry arm covers it. Taking the minimum is what makes it a lower
        # bound rather than a claim about our own output.
        ours_es = raw["categories"].get("entire staff insert/delete", 0)
        aud_es = es_by_row.get(rid)
        es = ours_es if aud_es is None else min(ours_es, aud_es)
        row["floor_estimator"] = {
            "ours_entire_staff": ours_es,
            "audiveris_entire_staff": aud_es,
            "used": es,
            "rule": "min over measured engines — a charge no reader avoided",
        }
        f_low = es / denom                          # structural charge alone
        f_high = (raw["omr_ed"] - nz["omr_ed"]) / denom   # everything the transform removed
        tier = "A_corroborated" if rid in corroborated else "B_single_source"
        row.update({
            "scoreable": True,
            "tier": tier,
            "ceiling_status": ("measured_and_corroborated" if tier == "A_corroborated"
                               else "measured_single_source"),
            "ceiling_caveat": (None if tier == "A_corroborated" else
                               "the floor is estimated from OUR OWN `entire staff` "
                               "count. The QUANTITY (truth vs hand-read page map) is "
                               "independent of us; the ESTIMATOR is not. Audiveris "
                               "does not corroborate this row — it is a two-system "
                               "page, or outside the arm it was run on."),
            "ceiling_kind": "structural",
            "ceiling_evidence": [
                "benchmarks/omr-scan-e2e-2026-09/works.json (hand-read staves map)",
                "benchmarks/omr-headline-validity-2026-09/results-normalised-arm.json",
                "benchmarks/omr-vs-industry-2026-09/categories-audiveris-scan11.json",
            ],
            "entire_staff_both_engines": es,
            "floor_low": f_low,
            "floor_high": f_high,
            "pct_of_achievable": pct_error(raw["omr_ned"], f_low),
            "pct_of_achievable_upper": pct_error(raw["omr_ned"], f_high),
            "pct_naive_no_ceiling": pct_error(raw["omr_ned"], 0.0),
        })
        scan_rows.append(row)

    # Pool by RECOMPUTING from counts, never by averaging percentages: a 3-bar
    # row and a 27-staff page must not carry equal weight.
    pool = [r for r in scan_rows if r.get("tier") == "A_corroborated"]
    ed = sum(r["raw_omr_ed"] for r in pool)
    den = sum(r["truth_symbols_raw"] + r["pred_symbols"] for r in pool)
    floor_num = sum(r["entire_staff_both_engines"] for r in pool)
    floor_den = sum(r["truth_symbols_raw"] + (r["truth_symbols_raw"] - 0) * 0 for r in pool)
    # the ideal denominator, per row, is truth_raw + truth_norm
    ideal_den = 0
    for r in norm["rows"]:
        if r["row_id"] in {p["row_id"] for p in pool}:
            ideal_den += r["raw"]["truth_symbols"] + r["norm"]["truth_symbols"]
    pooled_m = ed / den
    pooled_f = floor_num / ideal_den
    pool_b = [r for r in scan_rows if r.get("scoreable")]
    ed_b = sum(r["raw_omr_ed"] for r in pool_b)
    den_b = sum(r["truth_symbols_raw"] + r["pred_symbols"] for r in pool_b)
    ideal_b = 0
    for r in norm["rows"]:
        if r["row_id"] in {x["row_id"] for x in pool_b}:
            ideal_b += r["raw"]["truth_symbols"] + r["norm"]["truth_symbols"]
    es_b = sum(r["entire_staff_both_engines"] for r in pool_b)
    m_b, f_b = ed_b / den_b, es_b / ideal_b
    scan_pool_b = {
        "tier": "B_single_source",
        "n_rows": len(pool_b),
        "pooled_omr_ned": m_b,
        "pooled_floor_low": f_b,
        "pct_of_achievable": pct_error(m_b, f_b),
        "pct_naive_no_ceiling": pct_error(m_b, 0.0),
        "⚠️": "every normalisable row of the CANONICAL 20-row arm. The floor's "
              "estimator is our own `entire staff` count on 10 of the 15; on the "
              "other 5 an independent engine produces the identical number.",
    }
    scan_pool = {
        "tier": "A_corroborated",
        "n_rows": len(pool),
        "row_ids": [r["row_id"] for r in pool],
        "pooled_omr_ned": pooled_m,
        "pooled_floor_low": pooled_f,
        "pct_of_achievable": pct_error(pooled_m, pooled_f),
        "pct_naive_no_ceiling": pct_error(pooled_m, 0.0),
        "⚠️": "This pool is 5 of the scan gate's 20 rows and 3 of its 6 works. "
              "It is NOT the headline and may not be differenced against the "
              "20-row figure — different era, different arm.",
    }

    # ── engraved: reading F1, with the RENDER ceiling made explicit
    reading = json.loads(READING.read_text())
    agg = {}
    for w in reading["stage1_reading"].values():
        for fam, v in w["tolerances"]["0.5"]["per_family"].items():
            a = agg.setdefault(fam, [0, 0, 0])
            a[0] += v["truth"]; a[1] += v["pred"]; a[2] += v["matched"]

    def f1(t, p, m):
        if not t or not p:
            return None
        pr, rc = m / p, m / t
        return 2 * pr * rc / (pr + rc) if pr + rc else 0.0

    ship = [0, 0, 0]
    incl = [0, 0, 0]
    for fam, (t, p, m) in agg.items():
        if fam not in ("barline", "beam"):
            incl[0] += t; incl[1] += p; incl[2] += m
            if fam != "accidental":
                ship[0] += t; ship[1] += p; ship[2] += m
    reading_rows = {
        "metric": "stage-1 reading F1 vs exact Verovio page truth, 11 engraved works",
        "as_shipped_excludes_render_unreliable": f1(*ship),
        "if_render_unreliable_family_included": f1(*incl),
        "render_ceiling_worth_points": f1(*ship) - f1(*incl),
        "ceiling_kind": "render",
        "ceiling_evidence": "tools/omr/page_truth.py render_fidelity — Verovio draws "
                            "one accidental per <alter>, not per <accidental>; Brahms 1 "
                            "has 54 <accidental> and 149 <alter> and it drew 149",
        "pct_of_achievable": pct_rate(f1(*ship), 1.0),
        "note": "C = 1.0 is ASSUMED here (no measurement says a perfect reader "
                "could not reach F1 1.000 on the families we score), so this is "
                "conservative by the assumption-direction rule. The render "
                "ceiling is enacted as an EXCLUSION, not as a C < 1.",
    }

    # ── engraved OMR-NED: the structural floor is measured to be ZERO
    record = json.loads(RECORD.read_text())
    dt = record["runs"]["direction_text"]
    engraved = {
        "metric": "pooled OMR-NED, 11 engraved orchestral works",
        "omr_ned": dt["pooled"],
        "ceiling_kind": "structural",
        "floor": 0.0,
        "floor_evidence": "benchmarks/omr-headline-validity-2026-09/"
                          "engraved-normalise-noop.json — the page-normalising "
                          "transform is a NO-OP on all 11 (is_a_no_op: true), i.e. "
                          "these fixtures are 1:1 and carry no structural charge",
        "⚠️": "the no-op control was run at transform_version 1.0.0 and against "
              "the no_direction_text arm; the scan arm it certifies is 1.1.0 and "
              "direction-text-on. Re-running it is cheap and should be done.",
        "pct_of_achievable": pct_error(dt["pooled"], 0.0),
        "era_key": "orchestral-e2e/2026-09-02/11works/direction_text/%s" % dt["commit"],
    }

    # ── what the documented noise floor is worth in the new unit
    recon = json.loads(RECON.read_text())
    p = recon["pooled"]
    den20 = p["truth_symbols"] + p["pred_symbols"]
    noise = {
        "documented_noise_floor_edits": 6,
        "source": "CLAUDE.md — beethoven-984073-p4 scored 4673 then 4679 on two "
                  "runs of one tree",
        "pooled_denominator_20row": den20,
        "worth_in_omr_ned": 6.0 / den20,
        "worth_in_pct_of_achievable_at_floor_0": 100.0 * 6.0 / den20,
        "note": "on a single ROW the same 6 edits are worth far more — on "
                "beethoven-984073-p1 (denominator 1798) they are 0.33 OMR-NED "
                "points, i.e. ~0.46 points of % of achievable at floor 0 and "
                "~0.6 at its measured floor. A per-row delta must be compared "
                "against a PER-ROW noise floor.",
    }

    doc = {
        "generated_by": "benchmarks/omr-pipeline-audit-2026-09/probe/"
                        "probe_pct_of_achievable.py",
        "unit": "% of achievable, 0-100, higher is better, on every row",
        "transforms": {
            "error": "pct = 100 * (W - M) / (W - F); W = 1.0 for OMR-NED "
                     "(predict nothing); reversible: M = W - (pct/100)*(W - F)",
            "rate": "pct = 100 * V / C; reversible: V = C * pct/100",
        },
        "assumption_direction_rule": "an unknown ceiling is assumed at the value "
                                     "that MINIMISES the score (F=0 / C=1), so a "
                                     "missing ceiling can never manufacture 100",
        "scan": {"rows": scan_rows, "pool": scan_pool, "pool_all_normalisable": scan_pool_b,
                 "arm": norm.get("tag"), "transform_version": norm.get("transform_version"),
                 "git_head": norm.get("git_head"),
                 "arm_matches_headline": abs(
                     norm["pooled_raw_over_all_scored_rows"]["omr_ned"]
                     - json.loads(RECON.read_text())["pooled"]["omr_ned"]) < 1e-12},
        "engraved_reading": reading_rows,
        "engraved_omr_ned": engraved,
        "noise_floor": noise,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")

    print("SCAN — per row")
    for r in scan_rows:
        if r["scoreable"]:
            print("  %-34s NED %.4f  floor %.4f-%.4f  ->  %5.1f%%  (naive %5.1f%%)"
                  % (r["row_id"], r["raw_omr_ned"], r["floor_low"], r["floor_high"],
                     r["pct_of_achievable"], r["pct_naive_no_ceiling"]))
        else:
            print("  %-34s UNSCOREABLE — %s" % (r["row_id"], r["why"][:60]))
    print("\nSCAN pool B, every normalisable row (%d): NED %.4f floor %.4f -> %.1f%% (naive %.1f%%)"
          % (scan_pool_b["n_rows"], scan_pool_b["pooled_omr_ned"],
             scan_pool_b["pooled_floor_low"], scan_pool_b["pct_of_achievable"],
             scan_pool_b["pct_naive_no_ceiling"]))
    print("SCAN pool A (%d rows): NED %.4f floor %.4f -> %.1f%% (naive %.1f%%)"
          % (scan_pool["n_rows"], scan_pool["pooled_omr_ned"],
             scan_pool["pooled_floor_low"], scan_pool["pct_of_achievable"],
             scan_pool["pct_naive_no_ceiling"]))
    print("\nENGRAVED omr_ned %.4f floor 0.0 -> %.1f%%"
          % (engraved["omr_ned"], engraved["pct_of_achievable"]))
    print("ENGRAVED reading F1 %.4f (incl render-unreliable %.4f, worth %.4f) -> %.1f%%"
          % (reading_rows["as_shipped_excludes_render_unreliable"],
             reading_rows["if_render_unreliable_family_included"],
             reading_rows["render_ceiling_worth_points"],
             reading_rows["pct_of_achievable"]))
    print("\nNOISE 6 edits = %.5f NED = %.3f pct-points on the 20-row pool"
          % (noise["worth_in_omr_ned"], noise["worth_in_pct_of_achievable_at_floor_0"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
