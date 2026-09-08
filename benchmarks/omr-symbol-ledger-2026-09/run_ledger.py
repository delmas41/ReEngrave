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
    if len(staves) != n_pred_parts:
        reason = (f"the hand-verified lineup names {len(staves)} staves and the "
                  f"prediction emitted {n_pred_parts} parts — a positional join "
                  f"would be a guess")
        info["status"] = "unresolved"
        info["reason"] = reason
        return ([PartJoin(i, (), "unresolved", reason=reason, source="none")
                 for i in range(n_pred_parts)], info)
    join: list[PartJoin] = []
    for i, s in enumerate(staves):
        parts = tuple(int(p) for p in (s.get("parts") or [])) if isinstance(s, dict) else ()
        if parts:
            join.append(PartJoin(i, parts, "resolved"))
        else:
            join.append(PartJoin(i, (), "unresolved",
                                 reason="this staff names no reference part",
                                 source="works.json"))
    info["status"] = "resolved"
    info["staves_resolved"] = sum(1 for p in join if p.status == "resolved")
    info["staff_names"] = [s.get("name") if isinstance(s, dict) else str(s)
                           for s in staves]
    return join, info


# ---------------------------------------------------------------------------


def run(pairs_path: Path, out_dir: Path, detail: str,
        skip_musicdiff: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs = json.loads(pairs_path.read_text())
    rows_meta = load_rows()

    # ---- CONTROLS FIRST. Nothing below is quoted if these are not clean. ----
    controls = {"identity": [], "cross_parser": []}
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
    controls["ok"] = not controls["identity"] and not controls["cross_parser"]
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
    print(f"CONTROLS  identity+cross-parser over {controls['files_checked']} files: "
          f"{'CLEAN' if controls['ok'] else 'FAILED — nothing below may be quoted'}")
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
