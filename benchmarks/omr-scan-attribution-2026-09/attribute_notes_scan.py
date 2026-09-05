"""`wrong note` on the 20-row scan gate, attributed to a CAUSE per part.

`benchmarks/omr-ned-2026-08/attribute_wrong_notes.py` does this on the ENGRAVED
benchmark and REFUSES a work whose two sides disagree about how many parts
there are — pairing parts positionally is only defensible when both sides agree
on the count, and on an engraved fixture they always do. On a SCAN they almost
never do: a conductor's page condenses (Fl 1+2 on one staff) and suppresses
tacet staves, so 18 truth parts meet 11 predicted ones and that script declines
every row. Which is correct, and leaves the largest recognition bucket on this
pool unattributed.

THE PART PAIRING IS READ OUT OF musicdiff'S OWN ANSWER, not guessed —
`dump_part_coupling.py` writes it, reading `AnnPart.part_idx` off every
`inspart` / `delpart` op and zipping the survivors on each side. (⚠️ It cannot
come from `dump_ops.py`: that locates an op by the measure or note it holds,
and a part-level op holds neither, so all of them land at `part_index -1`.)

WITHIN a coupled part, bars are then paired BY INDEX, and only where the two
sides agree how many bars the part has. A part whose bar counts differ is
reported as `bar_count_mismatch` and contributes nothing: its notes are already
being charged as `entire measure insert/delete`, and aligning across a phase
slip would manufacture pitch errors that are really segmentation.

⚠️ SO THIS COVERS A SUBSET, AND THE SUBSET IS REPORTED. Read the coverage line
before any percentage below it: a cause distribution over 30% of the notes is a
statement about those notes.

Taxonomy is imported from the engraved script so the two sides speak one
language: exact / duration / order / shift:k / accid / mixed / count.

    python3 benchmarks/omr-scan-attribution-2026-09/attribute_notes_scan.py

MEASURED 2026-09-05. Coverage 2,390 of 5,907 truth notes in coupled parts
(40.5%). Over the covered bars:

    count     1,284 bars    the two sides disagree HOW MANY notes the bar has
    exact       889 bars
    shift:k     132 bars    every note off by a constant staff position
    mixed        45 bars
    duration     36 bars    every pitch right, a rhythm wrong
    accid        18 bars    right positions, wrong accidentals
    order         9 bars
    notes whose duration disagrees, across every class: 301

⚠️ THE SCAN SIDE'S DOMINANT NOTE FAILURE IS HOW MANY NOTES ARE IN THE BAR, NOT
WHICH ONES — the opposite of the engraved side, where CLAUDE.md records rhythm
as the dominant cause behind `wrong note`. Pitch geometry, rhythm and key
signature together are under 15% of the disagreeing bars.

⚠️ AND THE NEXT READING OF THAT IS WRONG WITHOUT A CONTROL. Inside the `count`
bars the prediction holds 2.17x the truth's notes and 516 are bars the truth
leaves empty, which reads as hallucination. It is the CONDENSATION confound —
see `probe_overproduction_control.py`, which measures 1.06x on the rows where
no part was left uncoupled.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/Users/seanjohnson/Desktop/ReEngrave/benchmarks/omr-ned-2026-08")

from attribute_wrong_notes import classify, measures_of  # noqa: E402

CANONICAL = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09/"
             "results-reconciliation.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path(CANONICAL))
    ap.add_argument("--coupling", type=Path,
                    default=HERE / "out" / "part_coupling.json")
    ap.add_argument("--json", type=Path, default=HERE / "out" / "wrong_note.json")
    args = ap.parse_args(argv)

    doc = json.loads(args.results.read_text())
    rows = [r for r in doc["rows"] if r.get("pooled")]
    coupling = json.loads(args.coupling.read_text())
    missing = {r["row_id"] for r in rows} - set(coupling)
    if missing:
        raise SystemExit(f"no part coupling for {sorted(missing)}")

    count_sides: Counter = Counter()
    pooled_classes: Counter = Counter()
    pooled_bars: Counter = Counter()
    dur_wrong = 0
    covered = uncovered = 0
    out_rows = []
    print(f"{'row':40s} {'pairs':>6s} {'aligned':>8s} {'skipped':>8s} "
          f"{'notes cov':>10s} {'notes unc':>10s}")
    for row in rows:
        rid = row["row_id"]
        truth = measures_of(Path(row["truth_xml"]))
        pred = measures_of(Path(row["pred_xml"]))
        cpl = coupling[rid]
        if (len(truth), len(pred)) != (cpl["n_truth_parts"], cpl["n_pred_parts"]):
            raise SystemExit(
                f"{rid}: music21 sees {len(truth)}/{len(pred)} parts, the "
                f"coupling was built over {cpl['n_truth_parts']}/"
                f"{cpl['n_pred_parts']} — the two are not the same score")
        pairs = [tuple(p) for p in cpl["pairs"]]

        classes: Counter = Counter()
        bars: Counter = Counter()
        r_dur = 0
        r_cov = r_unc = 0
        aligned = skipped = 0
        for t_i, p_i in pairs:
            t_bars, p_bars = truth[t_i]["bars"], pred[p_i]["bars"]
            n_t = sum(len(b) for b in t_bars)
            if len(t_bars) != len(p_bars):
                skipped += 1
                r_unc += n_t
                continue
            aligned += 1
            r_cov += n_t
            for t_bar, p_bar in zip(t_bars, p_bars):
                rec = classify(t_bar, p_bar)
                cls = ("shift" if rec["cls"].startswith("shift:")
                       else rec["cls"])
                bars[cls] += 1
                classes[cls] += rec["n"]
                r_dur += rec["dur_wrong"]
                if cls == "count":
                    # Which SIDE has more notes is the whole question for the
                    # class that dominates this pool, so keep both totals.
                    count_sides["truth"] += rec["n_truth"]
                    count_sides["pred"] += rec["n_pred"]
                    count_sides["bars_pred_over"] += rec["n_pred"] > rec["n_truth"]
                    count_sides["bars_pred_under"] += rec["n_pred"] < rec["n_truth"]
                    count_sides["bars_pred_empty"] += rec["n_pred"] == 0
                    count_sides["bars_truth_empty"] += rec["n_truth"] == 0
        pooled_classes.update(classes)
        pooled_bars.update(bars)
        dur_wrong += r_dur
        covered += r_cov
        uncovered += r_unc
        out_rows.append({"row_id": rid, "part_pairs": len(pairs),
                         "parts_aligned": aligned, "parts_skipped": skipped,
                         "notes_covered": r_cov, "notes_uncovered": r_unc,
                         "notes_by_class": dict(classes.most_common()),
                         "bars_by_class": dict(bars.most_common()),
                         "notes_wrong_duration": r_dur})
        print(f"{rid.replace('.reconciliation',''):40s} {len(pairs):>6d} "
              f"{aligned:>8d} {skipped:>8d} {r_cov:>10d} {r_unc:>10d}")

    total = covered + uncovered
    print(f"\nCOVERAGE  {covered} of {total} truth notes in coupled parts "
          f"({covered / total:.1%}) are in a part whose two sides agree on the "
          f"bar count and can be aligned; the rest are charged as entire "
          f"measure / entire staff and are not classified here.")
    print("\n== CAUSE OF DISAGREEMENT, over the covered notes ==")
    print(f"{'class':12s} {'notes':>8s} {'share':>7s} {'bars':>7s}")
    n_all = sum(pooled_classes.values()) or 1
    for cls, n in pooled_classes.most_common():
        print(f"{cls:12s} {n:>8d} {n / n_all:>6.1%} {pooled_bars[cls]:>7d}")
    print(f"\n⚠️ the `notes` column is max(truth, pred) per bar, so it exceeds "
          f"the covered truth notes wherever the prediction has MORE; read the "
          f"bar column beside it.")
    print(f"notes whose DURATION disagrees, across every class: {dur_wrong} "
          f"({dur_wrong / n_all:.1%})")
    print(f"\n== INSIDE THE `count` BARS — which side has more notes ==")
    print(f"  truth notes {count_sides['truth']}   predicted notes "
          f"{count_sides['pred']}   "
          f"(prediction/truth {count_sides['pred'] / max(count_sides['truth'], 1):.2f})")
    print(f"  bars where the prediction has MORE notes "
          f"{count_sides['bars_pred_over']}, FEWER "
          f"{count_sides['bars_pred_under']};  prediction empty "
          f"{count_sides['bars_pred_empty']}, truth empty "
          f"{count_sides['bars_truth_empty']}")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(
        {"covered_notes": covered, "uncovered_notes": uncovered,
         "notes_by_class": dict(pooled_classes.most_common()),
         "bars_by_class": dict(pooled_bars.most_common()),
         "notes_wrong_duration": dur_wrong, "count_bars": dict(count_sides),
         "rows": out_rows}, indent=2) + "\n")
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
