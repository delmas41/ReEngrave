"""Run the symbol ledger over the 20-row scan gate, and put it beside OMR-NED.

The ledger needs three inputs it must not derive, and all three already exist
as HAND-VERIFIED facts in `benchmarks/omr-scan-e2e-2026-09/works.json`:

  * `window.first_ref_measure` / `last_ref_measure` — the measure window,
    established by a probe that does not use the pipeline, carrying its own
    `confidence`.
  * `staves[i].parts` — which reference parts each PRINTED staff carries. This
    is the part correspondence, and it is the single biggest thing OMR-NED
    leaves unsettled (`entire staff insert/delete`, 16,777 edits).
  * `page.n_staves` — for the arity check below.

⚠️ **THE JOIN IS POSITIONAL AND IS ONLY TAKEN WHERE THE ARITY AGREES.** Our
export emits one part per stitched staff, so `staves[i]` joins to predicted
part `i` — but only when `len(staves) == len(pred parts)`. Where they differ
the row is declared `part_unresolved` in full rather than joined by guesswork,
and that declaration is a RESULT: it is the honest form of the charge
`entire staff insert/delete` is levying today.

⚠️ `staves` can be the STRING `"same-as:<row_id>"`. It is a real convention
with five separate resolvers in this repo and `mxl_verdicts._staff_specs` is
not one of them — it reads the string as 37 one-character staff names carrying
no parts. Resolved here.

    python3 benchmarks/omr-symbol-ledger-2026-09/run_ledger.py \\
        --pairs benchmarks/omr-wrongnote-decomposition-2026-09/scan-pairs.json \\
        --out-dir benchmarks/omr-symbol-ledger-2026-09/out
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.symbol_ledger import (  # noqa: E402
    PartJoin, build_ledger, cross_check_note_extraction, rows_to_csv,
    self_check_identity, summarise,
)

WORKS = ROOT / "benchmarks" / "omr-scan-e2e-2026-09" / "works.json"


def load_rows() -> dict[str, dict]:
    d = json.loads(WORKS.read_text())
    return {r["row_id"]: r for r in d["rows"]}


def staves_of(row: dict, rows: dict[str, dict]) -> tuple[list[dict] | None, str]:
    """The row's staff lineup, following `same-as:` aliases. (staves, source)"""
    st = row.get("staves")
    seen: set[str] = set()
    src = "own"
    while isinstance(st, str) and st.startswith("same-as:"):
        other = st.split(":", 1)[1].strip()
        if other in seen:
            return None, f"circular same-as at {other}"
        seen.add(other)
        src = f"same-as:{other}"
        nxt = rows.get(other)
        if nxt is None:
            return None, f"same-as names an unknown row {other}"
        st = nxt.get("staves")
    if not isinstance(st, list):
        return None, "no staves map on this row"
    return st, src


def expand_lineup(staves: list[dict]) -> list[dict | None]:
    """The lineup as one entry per PART WE COULD EMIT, or `None` where we emit
    none. This is what makes the arity check compare like with like.

    ⚠️ **THE OLD GATE COMPARED TWO DIFFERENT COUNTS AND CALLED THE DIFFERENCE A
    GUESS.** `len(staves)` is one entry per PRINTED staff, including one-line
    percussion rules; our part list is one per FIVE-LINE staff we detected. On
    the three Mahler rows the gap is exactly the one-line rules — 15−2=13,
    21−3=18, 21−4=17, matching `page.n_staves` and our part count to the staff
    — and each row's own `n_staves_note` already said in words *"compare
    `detected` against 13/18/17."* Refusing there declared 4,815 symbol rows
    `part_unresolved` for a units error.
    `benchmarks/omr-part-join-2026-09/FINDINGS.md`.

    Two declared shapes, both facts about the ENGRAVING and both now fields in
    `works.json` rather than prose:

    * `lines: 1` — a single-rule percussion staff. **A five-line staff
      detector cannot find it by construction**, so we emit no part for it and
      it drops out of the arity check. ⚠️ Spelled `lines`, not `one_line`:
      `benchmarks/omr-staves-map-completion-2026-09/candidate_maps.py` already
      proposed `lines=1` for this exact fact, and a second spelling of one fact
      is the `class_aliases.py` trap — 32 glyphs named twice, consumers written
      against one spelling. Renamed the same day, before anything depended on
      it. ⚠️ Its reference parts then belong to NO
      predicted part and stay `uncorresponded`, which is correct: that music is
      genuinely unread. This is a MEASUREMENT unlock, not a claim to read it.
    * `printed_staves: N` — one lineup entry the page prints as N staves
      (bach's `Cembalo (grand staff, 2 printed staves)`). We emit N parts; the
      **first** takes the reference parts and the rest are declared unresolved.
      ⚠️ NOT all N mapped to the same reference part — that would visit the
      same truth symbols N times and unbalance the ledger's own accounting
      control.
    """
    out: list[dict | None] = []
    for s in staves:
        if not isinstance(s, dict):
            out.append(None)
            continue
        if int(s.get("lines") or 5) != 5:
            continue                      # we emit no part for a one-line rule
        n = int(s.get("printed_staves") or 1)
        out.append(s)
        out.extend([None] * (n - 1))      # the extra printed staves of one entry
    return out


def part_join_for(row: dict, rows: dict[str, dict],
                  n_pred_parts: int) -> tuple[list[PartJoin], dict[str, Any]]:
    staves, src = staves_of(row, rows)
    info: dict[str, Any] = {"source": src, "n_staves_map": len(staves) if staves else 0,
                            "n_pred_parts": n_pred_parts,
                            "n_staves_printed": row.get("page", {}).get("n_staves")}
    if not staves:
        info["status"] = "unresolved"
        info["reason"] = src
        return ([PartJoin(i, (), "unresolved", reason=src, source="none")
                 for i in range(n_pred_parts)], info)
    slots = expand_lineup(staves)
    info["n_lineup_slots"] = len(slots)
    info["n_one_line_dropped"] = sum(
        1 for s in staves
        if isinstance(s, dict) and int(s.get("lines") or 5) != 5)
    info["n_extra_printed_staves"] = len(slots) - (len(staves)
                                                   - info["n_one_line_dropped"])
    if len(slots) != n_pred_parts:
        reason = (f"the hand-verified lineup expands to {len(slots)} five-line "
                  f"staves ({len(staves)} entries, "
                  f"{info['n_one_line_dropped']} one-line dropped, "
                  f"{info['n_extra_printed_staves']} extra printed) and the "
                  f"prediction emitted {n_pred_parts} parts — a positional join "
                  f"would be a guess")
        info["status"] = "unresolved"
        info["reason"] = reason
        return ([PartJoin(i, (), "unresolved", reason=reason, source="none")
                 for i in range(n_pred_parts)], info)
    join: list[PartJoin] = []
    for i, s in enumerate(slots):
        if s is None:
            join.append(PartJoin(
                i, (), "unresolved",
                reason="an extra printed staff of a lineup entry the reference "
                       "encodes as one part",
                source="works.json printed_staves"))
            continue
        parts = tuple(int(p) for p in (s.get("parts") or []))
        if parts:
            join.append(PartJoin(i, parts, "resolved"))
        else:
            join.append(PartJoin(i, (), "unresolved",
                                 reason="this staff names no reference part",
                                 source="works.json"))
    info["status"] = "resolved"
    info["staves_resolved"] = sum(1 for p in join if p.status == "resolved")
    info["staff_names"] = [(s.get("name") if isinstance(s, dict) else None)
                           for s in slots]
    return join, info


# ---------------------------------------------------------------------------


def run(pairs_path: Path, out_dir: Path, detail: str,
        skip_musicdiff: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = json.loads(pairs_path.read_text())
    rows_meta = load_rows()

    # ---- CONTROLS FIRST. Nothing below is quoted if these are not clean. ----
    controls = {"identity": [], "cross_parser": [], "unbalanced": []}
    for p in pairs:
        for f in (p["pred"], p["truth"]):
            si = self_check_identity(f)
            if not si["ok"]:
                controls["identity"].append({"file": f, "counts": si["counts"],
                                             "offenders": si["offenders"][:3]})
            cc = cross_check_note_extraction(f)
            if not cc["ok"]:
                controls["cross_parser"].append(
                    {"file": f, "n_mine": cc["n_mine"], "n_theirs": cc["n_theirs"],
                     "only_mine": cc["only_mine"][:3],
                     "only_theirs": cc["only_theirs"][:3]})
    controls["files_checked"] = len(pairs) * 2

    all_rows = []
    per_row: list[dict[str, Any]] = []
    for p in pairs:
        rid = p["name"]
        meta_row = rows_meta.get(rid, {})
        window = meta_row.get("window") or {}
        first = window.get("first_ref_measure")
        last = window.get("last_ref_measure")
        expected = (last - first + 1) if (first is not None and last is not None) else None

        # peek at the prediction's part count to decide the join arity
        from tools.omr.symbol_ledger import load_side
        _, pmeta = load_side(p["pred"], "pred")
        n_pred_parts = len(pmeta["parts"])
        join, join_info = part_join_for(meta_row, rows_meta, n_pred_parts)

        res = build_ledger(row_id=rid, pred_path=p["pred"], truth_path=p["truth"],
                           part_join=join, first_ref_measure=first,
                           expected_measures=expected)
        s = summarise(res)
        # ⚠️ THE ACCOUNTING CONTROL, READ. `coverage_check` has always been
        # computed and written to this file's own JSON, and nothing consumed
        # it — so it reported `balanced=False` on 5 of 7 joined scan rows for
        # as long as it existed and no run ever said so. Class C, in the
        # instrument built to make the metric legible.
        cov = res.coverage_check()
        if not cov["balanced"]:
            controls["unbalanced"].append({"row_id": rid, **cov})
        s["part_join_info"] = join_info
        s["window_confidence"] = window.get("confidence")
        if not skip_musicdiff:
            try:
                md = omr_ned.score_pair(pred=p["pred"], truth=p["truth"],
                                        detail=detail, name=rid)
                s["musicdiff"] = {
                    "omr_ned": md.get("omr_ned"), "omr_ed": md.get("omr_ed"),
                    "categories": {k: v for k, v in (md.get("categories") or {}).items() if v},
                }
            except Exception as exc:  # noqa: BLE001
                s["musicdiff"] = {"error": str(exc)[:300]}
        per_row.append(s)
        all_rows.extend(res.rows)
        oc = s["outcomes"]
        tot = sum(oc.values()) or 1
        pj = s["part_join_info"]
        print(f"{rid:<38} join={pj.get('status','?'):<10} "
              f"map/pred={pj.get('n_staves_map')}/{pj.get('n_pred_parts'):<3} "
              f"meas={s['measure_map']['status'][:4]:<4} "
              f"rows={tot:>5}  corresp={1 - oc.get('uncorresponded', 0)/tot:5.1%}")

    controls["ok"] = (not controls["identity"] and not controls["cross_parser"]
                      and not controls["unbalanced"])

    (out_dir / "ledger-rows.csv").write_text(rows_to_csv(all_rows))

    pooled = _pool(per_row, all_rows)
    report = {"detail": detail, "controls": controls, "pooled": pooled,
              "rows": per_row}
    (out_dir / "ledger-summary.json").write_text(json.dumps(report, indent=1))
    _print_pooled(pooled, controls)
    return 0 if controls["ok"] else 1


def _pool(per_row: list[dict], all_rows: list) -> dict[str, Any]:
    outcomes: Counter = Counter()
    reasons: Counter = Counter()
    attrs: Counter = Counter()
    attrs_weak: Counter = Counter()
    unassessable: Counter = Counter()
    fam_outcome: dict[str, Counter] = defaultdict(Counter)
    basis: Counter = Counter()
    md_cats: Counter = Counter()
    md_ed = 0
    for r in all_rows:
        outcomes[r.outcome] += 1
        fam_outcome[r.family][r.outcome] += 1
        if r.reason and r.outcome == "uncorresponded":
            reasons[r.reason] += 1
        if r.basis:
            basis["+".join(r.basis)] += 1
        tgt = attrs if r.basis_strength != "single_key" else attrs_weak
        for a in r.attrs_wrong:
            tgt[f"{r.family}.{a}"] += 1
        for a in r.attrs_not_assessable:
            unassessable[f"{r.family}.{a}"] += 1
    for s in per_row:
        md = s.get("musicdiff") or {}
        for k, v in (md.get("categories") or {}).items():
            md_cats[k] += v
        md_ed += md.get("omr_ed") or 0
    joined = [s for s in per_row if s["part_join_info"].get("status") == "resolved"]
    joined_ids = {s["row_id"] for s in joined}
    # ⚠️ The corresponded population, reported apart. Pooling the two would
    # let a page whose part join failed dilute — or inflate — the attribution
    # for pages where the join held. Same reason `boulanger` is not pooled
    # into the engraved benchmark.
    corr = Counter()
    corr_attrs = Counter()
    for r in all_rows:
        if r.row_id not in joined_ids:
            continue
        corr[r.outcome] += 1
        if r.basis_strength != "single_key":
            for a in r.attrs_wrong:
                corr_attrs[f"{r.family}.{a}"] += 1
    return {
        "n_rows": len(per_row),
        "rows_with_a_resolved_part_join": len(joined),
        "outcomes": dict(outcomes.most_common()),
        "uncorresponded_reasons": dict(reasons.most_common()),
        "attributes_wrong": dict(attrs.most_common()),
        "attributes_wrong_single_key": dict(attrs_weak.most_common()),
        "attributes_not_assessable": dict(unassessable.most_common()),
        "correspondence_basis": dict(basis.most_common()),
        "by_family": {k: dict(v.most_common()) for k, v in sorted(fam_outcome.items())},
        "musicdiff_categories": dict(md_cats.most_common()),
        "musicdiff_total_edits": md_ed,
        "join_resolved_rows": sorted(joined_ids),
        "corresponded_population": {
            "n_rows": len(joined_ids),
            "outcomes": dict(corr.most_common()),
            "attributes_wrong": dict(corr_attrs.most_common()),
        },
    }


def _print_pooled(p: dict[str, Any], controls: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print(f"CONTROLS  identity+cross-parser over {controls['files_checked']} files, "
          f"and per-row symbol accounting: "
          f"{'CLEAN' if controls['ok'] else 'FAILED — nothing below may be quoted'}")
    for u in controls.get("unbalanced", []):
        print(f"  ⚠️ UNBALANCED {u['row_id']}: {u['truth_symbols_in']} truth "
              f"symbols in, {u['truth_rows']} truth rows; {u['pred_symbols_in']} "
              f"pred in, {u['pred_accounted']} accounted")
    print("=" * 72)
    tot = sum(p["outcomes"].values()) or 1
    print(f"\n{p['n_rows']} rows, {p['rows_with_a_resolved_part_join']} with a "
          f"resolved part join.  {tot} symbol rows.\n")
    print("LEDGER OUTCOMES")
    for k, v in p["outcomes"].items():
        print(f"  {k:<28}{v:>8}  {v/tot:6.1%}")
    print("\n  uncorresponded, by which tier failed")
    for k, v in p["uncorresponded_reasons"].items():
        print(f"    {k:<26}{v:>8}")
    print("\nNAMED ATTRIBUTE ERRORS (corroborated pairings)")
    for k, v in list(p["attributes_wrong"].items())[:14]:
        print(f"  {k:<28}{v:>8}")
    if p["attributes_wrong_single_key"]:
        print("\n  from a SINGLE-KEY pairing (uncorroborated — reported apart)")
        for k, v in list(p["attributes_wrong_single_key"].items())[:8]:
            print(f"    {k:<26}{v:>8}")
    if p["attributes_not_assessable"]:
        print("\nNOT ASSESSABLE — the pairing used the attribute, so it cannot report on it")
        for k, v in list(p["attributes_not_assessable"].items())[:8]:
            print(f"  {k:<28}{v:>8}")
    cp = p["corresponded_population"]
    ct = sum(cp["outcomes"].values()) or 1
    print(f"\n--- restricted to the {cp['n_rows']} rows whose PART JOIN RESOLVED "
          f"({ct} symbol rows) ---")
    for k, v in cp["outcomes"].items():
        print(f"  {k:<28}{v:>8}  {v/ct:6.1%}")
    print("  named attribute errors, corroborated:")
    for k, v in list(cp["attributes_wrong"].items())[:10]:
        print(f"    {k:<26}{v:>8}")
    if p["musicdiff_categories"]:
        print(f"\nMUSICDIFF on the same pairs — {p['musicdiff_total_edits']} edits")
        for k, v in list(p["musicdiff_categories"].items())[:10]:
            print(f"  {k:<28}{v:>8}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pairs", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=BENCH / "out")
    ap.add_argument("--detail", default="AllObjects")
    ap.add_argument("--no-musicdiff", action="store_true")
    a = ap.parse_args(argv)
    return run(a.pairs, a.out_dir, a.detail, a.no_musicdiff)


if __name__ == "__main__":
    sys.exit(main())
