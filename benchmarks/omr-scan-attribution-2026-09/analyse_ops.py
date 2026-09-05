"""Split the scan gate's two biggest buckets into causes, from the op lists.

Runs on the HOST python over `out/ops/*.json` (from `dump_all_ops.py`) and
`out/part_coupling.json` (from `dump_part_coupling.py`). Stdlib only.

FOUR THINGS IT ANSWERS.

A. CATEGORY RECONCILIATION, because musicdiff has a silent fallback.
   `Visualization.get_omr_ed_dict` maps an op name it does not know to
   `directionins` — i.e. into "wrong direction" — instead of failing. At
   `DetailLevel.AllObjects`, the level this benchmark runs at, `pitchnameedit`,
   `pitchtypeedit`, `inspitch`, `delpitch`, `voiceins` and `voicedel` are all
   unmapped (they live in `_VOICING_HEADER_NAME_OF_EDIT_NAME_EXTRAS`, merged in
   only when Voicing is on). `dump_ops` does no such fallback — it reports
   `?(name)` — so comparing the two says whether "wrong direction" is a mixed
   bucket on this pool, and by how much.

B. `entire staff insert/delete` = `inspart` / `delpart`, priced at the whole
   part's notation size. Not an opinion about the music: the price of a part
   existing on one side only.

C. `entire measure insert/delete` = `insbar` / `delbar`. Two splits:
   the SIDE (`insbar` costs the TRUTH bar — music we never produced; `delbar`
   costs the PREDICTED bar — music we produced that never paired), and the
   PHASE (within a coupled part, `min(insbar, delbar)` bars sit in slots where
   both sides have a bar; `|insbar - delbar|` is a raw bar-count shortfall).

   ⚠️ THE AMPLIFICATION TRAP IS A READING TRAP, NOT AN OVERCHARGE.
   `Comparison._block_diff_lin` is a cost-MINIMISING dynamic program over bars:
   at each slot it prices delbar, insbar and editbar and keeps the cheapest. A
   bar pair is therefore only ever charged whole-plus-whole where pairing them
   elementwise would have cost MORE. CLAUDE.md's fermata example is real as a
   reading trap — one changed symbol can push a slot past the pairing cost once
   the sequence is out of phase — but the bucket is a LOWER bound on the
   elementwise cost of the same bars. None of it is recoverable by re-scoring.

D. `wrong note` = `noteins` (truth-only note, MISSED) + `notedel`
   (prediction-only, INVENTED). ⚠️ NEITHER COSTS 1: each is priced at the
   note's notation size (measured on this pool, 3.65 and 3.09 on average), so
   counting ops and reading edits are different questions and both are printed.
   The cause breakdown lives in `attribute_notes_scan.py`; the ins/del join
   cannot be done here because a `noteins` carries a TRUTH part index and a
   `notedel` a PREDICTED one, and on a scan those are different numbers.

    python3 benchmarks/omr-scan-attribution-2026-09/analyse_ops.py

MEASURED 2026-09-05 on the 20-row gate (74,968 edits, 14,902 ops, 30 op names;
every row reproduces its recorded OMR-ED exactly).

A. Zero unmapped ops — `wrong direction` is not absorbing anything here, and
   zero `pitchnameedit` fired, as AllObjects requires.

B. entire staff 17,520 = inspart 16,342 (148 truth parts never produced)
   + delpart 1,178 (9 predicted parts that never coupled).
   ⚠️ EVERY inspart IS CONDENSATION: truth part counts 11/15/18/21/38 against
   12-19 printed staves, on rows whose predicted staff count matches the
   printed one exactly. All 9 delparts are on the three rows where
   `export._stitch_slots` refused.

C. entire measure 29,685 = insbar 13,522 (2,598 truth bars never paired)
   + delbar 16,163 (1,860 predicted bars never paired).
   By phase: 1,806 bars in slots BOTH sides filled, 846 in one-sided slots —
   and 620 of those 846 are the two Beethoven p3 rows alone.
   ⚠️ BAR SEGMENTATION IS NOT THE PROBLEM ON 17 OF 20 ROWS: per-part bar
   counts agree within one everywhere except beethoven-5 984073/575951 p3
   (truth 34 x 18 parts; predicted 16 x 11 and 18 x 8) and brahms-1 p2
   (truth 15 x 21; predicted 7 x 14 and 8 x 13). 16+18=34 and 7+8=15 — the
   bars are all there, emitted as one part per SYSTEM because the stitcher
   refuses when a page's systems disagree on staff count. Those three rows
   carry 16,769 edits, 22.4% of the gate.

D. wrong note 22,165 = noteins 2,647 ops / 9,666 edits (3.65 each, MISSED)
   + notedel 4,040 ops / 12,499 edits (3.09 each, INVENTED).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANONICAL = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
             "reconciliation/benchmarks/omr-scan-e2e-2026-09/"
             "results-reconciliation.json")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path(CANONICAL))
    ap.add_argument("--ops-dir", type=Path, default=HERE / "out" / "ops")
    ap.add_argument("--coupling", type=Path,
                    default=HERE / "out" / "part_coupling.json")
    ap.add_argument("--json", type=Path, default=HERE / "out" / "attribution.json")
    args = ap.parse_args(argv)

    doc = json.loads(args.results.read_text())
    rows = {r["row_id"]: r for r in doc["rows"] if r.get("pooled")}
    coupling = json.loads(args.coupling.read_text())
    dumps = {}
    for path in sorted(args.ops_dir.glob("*.json")):
        d = json.loads(path.read_text())
        dumps[d["row_id"]] = d

    # Prove we looked at something before any comparison is reported.
    for label, have in (("op dump", dumps), ("coupling", coupling)):
        missing = set(rows) - set(have)
        if missing:
            raise SystemExit(f"no {label} for {sorted(missing)}")
    for rid, d in dumps.items():
        if not d["cost_matches_recorded"]:
            raise SystemExit(f"{rid}: dump cost {d['total_cost']} != recorded "
                             f"{d['recorded_omr_ed']}")
    total_ops = sum(d["n_ops"] for d in dumps.values())
    total_cost = sum(d["total_cost"] for d in dumps.values())
    if total_cost != doc["pooled"]["omr_ed"]:
        raise SystemExit("dumped cost does not sum to the pooled OMR-ED")
    print(f"rows {len(dumps)}   ops {total_ops}   cost {total_cost}   "
          f"== pooled OMR-ED {doc['pooled']['omr_ed']}")

    order = sorted(dumps, key=lambda r: -dumps[r]["total_cost"])

    # ---- A ---------------------------------------------------------------
    print("\n== A. CATEGORY RECONCILIATION ==")
    # Test the OP NAMES, not dump_ops' category strings: dump_ops does not
    # apply musicdiff's `extra.kind` rewrite, so its categories are coarser for
    # the `extra*` family and a `?()` bucket would not be evidence either way.
    voicing_only = {"pitchnameedit", "pitchtypeedit", "inspitch", "delpitch",
                    "voiceins", "voicedel"}
    unmapped: Counter = Counter()
    seen_names: Counter = Counter()
    for d in dumps.values():
        for name, cost in d["cost_by_name"].items():
            seen_names[name] += cost
            if name in voicing_only:
                unmapped[name] += cost
    print(f"  {len(seen_names)} distinct op names fired, {sum(seen_names.values())} "
          f"edits — the proof this looked at something.")
    if unmapped:
        print("  op names musicdiff cannot map at AllObjects — it files these "
              "silently under 'wrong direction':")
        for name, cost in unmapped.most_common():
            print(f"    {name:24s} {cost:>6d}")
    else:
        print("  none: every op emitted on this pool is in musicdiff's header "
              "map, so no category is silently absorbing another. In "
              "particular ZERO `pitchnameedit` ops fired — at AllObjects notes "
              "are paired BY PITCH, so a pitch error cannot be an edit inside "
              "a paired note and necessarily becomes noteins + notedel. "
              "`wrong pitch` is structurally unreachable, not empirically zero.")

    # ---- B ---------------------------------------------------------------
    print("\n== B. ENTIRE STAFF (inspart / delpart) ==")
    print(f"{'row':40s} {'t.parts':>8s} {'p.parts':>8s} {'coupled':>8s} "
          f"{'inspart':>8s} {'cost':>7s} {'delpart':>8s} {'cost':>7s}")
    staff_rows = []
    b_ins = b_del = 0
    for rid in order:
        d, c = dumps[rid], coupling[rid]
        ins = [r for r in d["rows"] if r["op"] == "inspart"]
        dele = [r for r in d["rows"] if r["op"] == "delpart"]
        ic, dc = sum(r["cost"] for r in ins), sum(r["cost"] for r in dele)
        b_ins += ic
        b_del += dc
        staff_rows.append({"row_id": rid, "inspart": len(ins), "inspart_cost": ic,
                           "delpart": len(dele), "delpart_cost": dc,
                           "truth_parts": c["n_truth_parts"],
                           "pred_parts": c["n_pred_parts"],
                           "coupled": len(c["pairs"])})
        print(f"{rid.replace('.reconciliation',''):40s} "
              f"{c['n_truth_parts']:>8d} {c['n_pred_parts']:>8d} "
              f"{len(c['pairs']):>8d} {len(ins):>8d} {ic:>7d} "
              f"{len(dele):>8d} {dc:>7d}")
    print(f"  TOTAL  inspart {b_ins} edits (truth parts never produced)   "
          f"delpart {b_del} edits (parts produced that never coupled)")

    # ---- C ---------------------------------------------------------------
    # An insbar carries a TRUTH part index and a delbar a PREDICTED one, so the
    # two are counted in their own frames and joined through the coupling.
    print("\n== C. ENTIRE MEASURE (insbar / delbar) ==")
    print(f"{'row':40s} {'insbar':>7s} {'cost':>7s} {'delbar':>7s} {'cost':>7s} "
          f"{'both-sided':>11s} {'one-sided':>10s}")
    meas_rows = []
    c_ins = c_del = c_both = c_one = 0
    for rid in order:
        d, c = dumps[rid], coupling[rid]
        t2p = {t: p for t, p in c["pairs"]}
        ins_by: Counter = Counter()
        del_by: Counter = Counter()
        ins_cost = del_cost = 0
        for r in d["rows"]:
            if r["op"] == "insbar":
                ins_by[t2p.get(r["part_index"], f"uncoupled-t{r['part_index']}")] += 1
                ins_cost += r["cost"]
            elif r["op"] == "delbar":
                del_by[r["part_index"]] += 1
                del_cost += r["cost"]
        both = sum(min(ins_by[k], del_by[k]) for k in set(ins_by) | set(del_by))
        one = sum(abs(ins_by[k] - del_by[k]) for k in set(ins_by) | set(del_by))
        c_ins += ins_cost
        c_del += del_cost
        c_both += both
        c_one += one
        meas_rows.append({"row_id": rid, "insbar": sum(ins_by.values()),
                          "insbar_cost": ins_cost, "delbar": sum(del_by.values()),
                          "delbar_cost": del_cost, "both_sided_bars": both,
                          "one_sided_bars": one})
        print(f"{rid.replace('.reconciliation',''):40s} "
              f"{sum(ins_by.values()):>7d} {ins_cost:>7d} "
              f"{sum(del_by.values()):>7d} {del_cost:>7d} {both:>11d} {one:>10d}")
    print(f"  TOTAL  insbar {c_ins} edits (truth bars never paired)   "
          f"delbar {c_del} edits (predicted bars never paired)")
    print(f"         bars in slots BOTH sides filled {c_both}   "
          f"bars in one-sided slots (bar-count shortfall) {c_one}")

    # ---- D ---------------------------------------------------------------
    print("\n== D. WRONG NOTE, by side (ops and edits) ==")
    print(f"{'row':40s} {'noteins':>8s} {'edits':>7s} {'notedel':>8s} "
          f"{'edits':>7s}")
    note_rows = []
    d_i = d_d = d_ic = d_dc = 0
    for rid in order:
        d = dumps[rid]
        ins = [r for r in d["rows"] if r["op"] == "noteins"]
        dele = [r for r in d["rows"] if r["op"] == "notedel"]
        ic, dc = sum(r["cost"] for r in ins), sum(r["cost"] for r in dele)
        d_i += len(ins)
        d_d += len(dele)
        d_ic += ic
        d_dc += dc
        note_rows.append({"row_id": rid, "noteins": len(ins), "noteins_cost": ic,
                          "notedel": len(dele), "notedel_cost": dc})
        print(f"{rid.replace('.reconciliation',''):40s} {len(ins):>8d} "
              f"{ic:>7d} {len(dele):>8d} {dc:>7d}")
    print(f"  TOTAL  {d_i} truth notes never paired = {d_ic} edits "
          f"({d_ic / max(d_i, 1):.2f}/note);  {d_d} predicted notes never "
          f"paired = {d_dc} edits ({d_dc / max(d_d, 1):.2f}/note)")

    payload = {"results": str(args.results), "ops_dir": str(args.ops_dir),
               "unmapped_ops": dict(unmapped),
               "entire_staff": {"rows": staff_rows, "inspart_cost": b_ins,
                                "delpart_cost": b_del},
               "entire_measure": {"rows": meas_rows, "insbar_cost": c_ins,
                                  "delbar_cost": c_del,
                                  "both_sided_bars": c_both,
                                  "one_sided_bars": c_one},
               "wrong_note": {"rows": note_rows, "noteins": d_i,
                              "noteins_cost": d_ic, "notedel": d_d,
                              "notedel_cost": d_dc}}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
