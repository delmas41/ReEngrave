"""Is the scan side's note OVER-PRODUCTION real, or an artifact of condensation?

`attribute_notes_scan.py` reports that inside the bars where the two sides
disagree how many notes there are, the prediction holds 2.17x the truth's notes
and 516 of those bars are EMPTY in the truth. Read naively that says the reader
hallucinates. It cannot be read naively, because of the confound this file
exists to remove:

⚠️ A CONDENSED STAFF CARRIES TWO PARTS' NOTES AND IS SCORED AGAINST ONE. The
reference encodes Fl 1 and Fl 2 separately; the page prints them on one staff;
musicdiff couples our one staff to ONE of the two truth parts and charges the
other as `inspart`. Every note of the second flute is then a note we have and
"the truth" does not — over-production by construction, on a page we read
correctly.

THE CONTROL is the rows where no part was uncoupled at all: truth parts ==
predicted parts, zero `inspart`, zero `delpart`. On this pool that is the three
Dvorak rows. If over-production survives there it is the reader; if it
disappears it was the confound.

    python3 benchmarks/omr-scan-attribution-2026-09/probe_overproduction_control.py

MEASURED 2026-09-05 — IT WAS THE CONFOUND, NOT THE READER:

    arm                          rows  bars  truth  pred  pred/truth  t-empty
    clean (no uncoupled part)       3   450    905   956      1.06        11
    condensed (inspart > 0)         9  1963   1485  3398      2.29       505

⚠️ The clean arm is one work, one publisher, three pages — a window, not a
population.

The same split over the whole gate's recorded categories says why this matters
beyond one statistic:

    arm          rows  OMR-NED   edits  e.staff        e.measure      wrong note
    clean           3   0.6810   8,945  0     (0%)     1,051 (11.7%)  6,809 (76.1%)
    condensed      17   0.8728  66,023  17,520 (26.5%) 28,634 (43.4%) 15,356 (23.3%)

On the rows where the truth's part structure and the page's agree, the gate IS
a recognition measurement — three quarters `wrong note`, `entire staff` zero.
On the other seventeen it is mostly a measurement of the mismatch.
"""
from __future__ import annotations

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


def main() -> int:
    doc = json.loads(Path(CANONICAL).read_text())
    coupling = json.loads((HERE / "out" / "part_coupling.json").read_text())
    rows = [r for r in doc["rows"] if r.get("pooled")]

    arms: dict[str, Counter] = {"clean (no uncoupled part)": Counter(),
                                "condensed (inspart > 0)": Counter()}
    members: dict[str, list[str]] = {k: [] for k in arms}
    for row in rows:
        rid = row["row_id"]
        c = coupling[rid]
        if c["inspart_truth_idx"] or c["delpart_pred_idx"]:
            arm = "condensed (inspart > 0)"
        else:
            arm = "clean (no uncoupled part)"
        truth = measures_of(Path(row["truth_xml"]))
        pred = measures_of(Path(row["pred_xml"]))
        acc = arms[arm]
        used = False
        for t_i, p_i in c["pairs"]:
            t_bars, p_bars = truth[t_i]["bars"], pred[p_i]["bars"]
            if len(t_bars) != len(p_bars):
                continue
            used = True
            for t_bar, p_bar in zip(t_bars, p_bars):
                rec = classify(t_bar, p_bar)
                acc["bars"] += 1
                acc["truth_notes"] += len(t_bar)
                acc["pred_notes"] += len(p_bar)
                if rec["cls"] != "count":
                    continue
                acc["count_bars"] += 1
                acc["count_truth"] += rec["n_truth"]
                acc["count_pred"] += rec["n_pred"]
                acc["truth_empty"] += rec["n_truth"] == 0
                acc["pred_empty"] += rec["n_pred"] == 0
        if used:
            members[arm].append(rid.replace(".reconciliation", ""))

    for arm, acc in arms.items():
        print(f"\n== {arm} ==")
        print("  rows:", ", ".join(members[arm]) or "(none aligned)")
        if not acc["bars"]:
            continue
        print(f"  aligned bars {acc['bars']}   truth notes {acc['truth_notes']}"
              f"   predicted notes {acc['pred_notes']}   "
              f"pred/truth {acc['pred_notes'] / max(acc['truth_notes'], 1):.2f}")
        print(f"  bars disagreeing on note count {acc['count_bars']}: truth "
              f"{acc['count_truth']} vs predicted {acc['count_pred']} "
              f"({acc['count_pred'] / max(acc['count_truth'], 1):.2f}x); "
              f"truth-empty {acc['truth_empty']}, pred-empty {acc['pred_empty']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
