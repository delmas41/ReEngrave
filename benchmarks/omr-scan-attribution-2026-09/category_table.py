"""The scan gate's OMR-NED budget, by musicdiff category — pooled and per row.

WHY THIS EXISTS. Every ranking decision on the scan side has been made from
attributions of the OLD 5-row and 11-row pools. The gate is now a 20-row era
(`benchmarks/omr-scan-e2e-2026-09/results-reconciliation.json`), and nobody had
broken its 74,968 edits out by category. This is that map.

FIXTURE PROVENANCE IS THE FIRST THING IT CHECKS, because the main checkout's
`fixtures/` still holds the ELEVEN-row `.restamp-composed` set and a script
pointed there measures the old gate while looking like it measured this one.
The 20-row transcriptions carry the suffix `.reconciliation.omr.json` and live
in the `reconciliation` worktree; `--expect-suffix` asserts it and the run dies
rather than reporting an unlabelled number.

IT ALSO PROVES IT LOOKED AT SOMETHING before it reports anything, which this
repo has been burned for skipping (2026-09-04: a regex that matched nothing, a
control arm restored from the git index). Three independent identities are
asserted, not assumed:

    * row count == --expect-rows
    * sum of per-row omr_ed == pooled omr_ed
    * per row and pooled, sum of the category counts == that omr_ed
    * every pred/truth XML named by a row exists on disk

Reads only the canonical results file. Writes nothing into it.

MEASURED 2026-09-05 — pooled OMR-NED 0.8444, OMR-ED 74,968, 49,846 truth
symbols against 38,937 predicted, 20 rows:

    entire measure insert/delete   29,685  39.6%
    wrong note                     22,165  29.6%
    entire staff insert/delete     17,520  23.4%
    wrong note head                 1,786   2.4%
    wrong flag/beam                   687   0.9%
    wrong dynamic 512, keysig 507, direction 500, timesig 468, dot 282,
    slur 220, clef 205, accidental 82, tie 68, articulation 56, lyric 48,
    crescendo 44, barline 42, ornament 37, diminuendo 32, tuplet 12,
    fingered tremolo 6, tempo 4

⚠️ THE 63% FIGURE IS CONFIRMED ON THE DEFAULT ARM. entire staff + entire
measure = 47,205 of 74,968 = 62.97%, against the structural workstream's
47,181 of 74,962 on the flags-off arm — 24 edits between two different arms.

THREE BUCKETS ARE 92.5% of the gate (69,370). Everything else together is
5,598 edits, 7.5%, and no single one exceeds 0.9%.

⚠️ NO CATEGORY ON THIS POOL IS ONE PAGE'S ARTIFACT — the concentration column
is the check. The three big buckets spread 9-19% across their worst row, and
every bucket whose worst row exceeds 30% is under 700 edits.

    python3 benchmarks/omr-scan-attribution-2026-09/category_table.py \
        --results /abs/path/to/results-reconciliation.json \
        --json out/categories.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CANONICAL = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09/"
             "results-reconciliation.json")


def load(results: Path, expect_rows: int, expect_suffix: str) -> dict:
    doc = json.loads(results.read_text())
    rows = [r for r in doc["rows"] if r.get("pooled")]
    if len(rows) != expect_rows:
        raise SystemExit(f"expected {expect_rows} pooled rows, got {len(rows)}")

    # Provenance: every row must name the fixture generation this report claims.
    for row in rows:
        for key in ("pred_xml", "truth_xml"):
            path = Path(row[key])
            if not path.is_file():
                raise SystemExit(f"{row['row_id']}: missing {key} {path}")
        if expect_suffix not in Path(row["pred_xml"]).name:
            raise SystemExit(
                f"{row['row_id']}: pred_xml {Path(row['pred_xml']).name!r} does "
                f"not carry {expect_suffix!r} — wrong fixture generation")

    pooled = doc["pooled"]
    ed_sum = sum(r["omr_ned"]["omr_ed"] for r in rows)
    if ed_sum != pooled["omr_ed"]:
        raise SystemExit(f"row omr_ed sums to {ed_sum}, pooled says "
                         f"{pooled['omr_ed']}")
    for name, cats, ed in ([("POOLED", pooled["categories"], pooled["omr_ed"])]
                           + [(r["row_id"], r["omr_ned"]["categories"],
                               r["omr_ned"]["omr_ed"]) for r in rows]):
        if sum(cats.values()) != ed:
            raise SystemExit(f"{name}: categories sum to {sum(cats.values())}, "
                             f"omr_ed is {ed}")
    return {"doc": doc, "rows": rows, "pooled": pooled}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path(CANONICAL))
    ap.add_argument("--expect-rows", type=int, default=20)
    ap.add_argument("--expect-suffix", default=".reconciliation.")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    got = load(args.results, args.expect_rows, args.expect_suffix)
    rows, pooled = got["rows"], got["pooled"]

    print(f"results     {args.results}")
    print(f"fixtures    {Path(rows[0]['pred_xml']).parent}")
    print(f"rows {len(rows)}   pooled OMR-NED {pooled['omr_ned']:.4f}   "
          f"OMR-ED {pooled['omr_ed']}   truth syms {pooled['truth_symbols']}   "
          f"pred syms {pooled['pred_symbols']}")

    # 1 — the pooled table, largest first, with each category's concentration:
    #     the single row holding the largest share of it. A bucket that is one
    #     page's artifact has to be visible as one.
    per_row_cat = {r["row_id"]: r["omr_ned"]["categories"] for r in rows}
    print("\n== 1. POOLED CATEGORY TABLE ==")
    print(f"{'category':34s} {'edits':>7s} {'share':>7s}  "
          f"{'top row':>7s}  worst row")
    ranked = sorted(pooled["categories"].items(), key=lambda kv: -kv[1])
    table = []
    for cat, n in ranked:
        if n == 0:
            continue
        contrib = Counter({rid: c.get(cat, 0) for rid, c in per_row_cat.items()})
        worst, worst_n = contrib.most_common(1)[0]
        share = n / pooled["omr_ed"]
        top = worst_n / n
        table.append({"category": cat, "edits": n, "share": share,
                      "top_row": worst, "top_row_edits": worst_n,
                      "top_row_share": top,
                      "n_rows_nonzero": sum(1 for v in contrib.values() if v)})
        print(f"{cat:34s} {n:>7d} {share:>6.1%}  {top:>6.0%}  "
              f"{worst.replace('.reconciliation',''):s}")

    # 2 — per row. Same budget, sliced the other way.
    print("\n== 2. PER-ROW ==")
    head = ["e.staff", "e.measure", "wrong note", "other"]
    print(f"{'row':40s} {'OMR-NED':>8s} {'edits':>7s}"
          + "".join(f"{h:>11s}" for h in head))
    per_row = []
    for r in sorted(rows, key=lambda r: -r["omr_ned"]["omr_ed"]):
        c = r["omr_ned"]["categories"]
        ed = r["omr_ned"]["omr_ed"]
        staff = c.get("entire staff insert/delete", 0)
        meas = c.get("entire measure insert/delete", 0)
        note = c.get("wrong note", 0)
        other = ed - staff - meas - note
        per_row.append({"row_id": r["row_id"], "label": r.get("label"),
                        "omr_ned": r["omr_ned"]["omr_ned"], "omr_ed": ed,
                        "entire_staff": staff, "entire_measure": meas,
                        "wrong_note": note, "other": other,
                        "truth_parts": r["truth"]["parts"],
                        "pred_parts": (r.get("notes") or {}).get("n_pred_parts"),
                        "printed_staves": r["printed"]["staves"],
                        "truth_measures": r["truth"]["measures"],
                        "detected_measures": r["detected"].get("measures"),
                        "categories": c})
        print(f"{r['row_id'].replace('.reconciliation',''):40s} "
              f"{r['omr_ned']['omr_ned']:>8.4f} {ed:>7d}"
              + "".join(f"{v:>11d}" for v in (staff, meas, note, other)))

    print("\n== 2b. STRUCTURE PER ROW (truth parts vs predicted parts) ==")
    print(f"{'row':40s} {'t.parts':>8s} {'p.parts':>8s} {'printed':>8s} "
          f"{'t.meas':>7s} {'d.meas':>7s} {'e.staff':>8s}")
    for p in sorted(per_row, key=lambda p: -p["entire_staff"]):
        print(f"{p['row_id'].replace('.reconciliation',''):40s} "
              f"{p['truth_parts']:>8d} {str(p['pred_parts']):>8s} "
              f"{p['printed_staves']:>8d} {p['truth_measures']:>7d} "
              f"{str(p['detected_measures']):>7s} {p['entire_staff']:>8d}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(
            {"results": str(args.results),
             "fixtures": str(Path(rows[0]["pred_xml"]).parent),
             "pooled": pooled, "categories": table, "rows": per_row},
            indent=2) + "\n")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
