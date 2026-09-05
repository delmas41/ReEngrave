"""Phase 4 step 1: what bracket evidence does the 20-row scan corpus actually hold?

The staff-identity audit measured a staff's bracket BLOCK predicting its
instrument FAMILY at 0.857 within-block vs 0.039 page-wide, with block
boundaries 22/22 precise and 22/39 recalled — over 12 systems of a DIFFERENT
corpus. Those numbers are not inherited here. This measures the same properties
on the rows this workstream is priced against, before anything is built.

WHERE THE EVIDENCE LIVES. `system_grouping._assign_groups` sets
`Staff.group_index`, but it is NOT serialized onto the staff dicts — it reaches
the result JSON only through `contextual["reference"]`, as
`{"slot": n, "group": g, "instrument": …}`. So a row whose contextual pass
abstained carries no bracket evidence at all, which is itself a coverage fact.

THE FAMILY TRUTH is the hand-read printed name from `works.json`, put through
`instruments.lookup` for its family. The printed name is human-verified and the
lexicon is shared, so this does not consult the pipeline's own instrument
reading — which Phase 1 showed is a restatement of the ordinal join.

⚠️ `reference` IS SLOT-INDEXED, and a slot is the ordinal join's. On
`beethoven-sym5-mvt1-*-p4` the join succeeds and is still wrong (slots 6-10 are
shifted by one), so that row's block-to-family comparison inherits the
mis-join. It is reported separately rather than pooled.

⚠️ CEILING-FREE. Nothing here reads a dossier; `works.json`'s printed names are
hand-read from the page, so this probe carries no answer-key contamination.

FIXTURE PROVENANCE. 20-row transcriptions from
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. The main checkout's `fixtures/` still holds
the ELEVEN-row era's `.restamp-composed` set.

    python3 benchmarks/omr-structural-parts-2026-09/probe_bracket_blocks.py --json bracket-blocks.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from tools.omr.instruments import lookup  # noqa: E402

FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"
WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"

#: Rows whose slot space is known mis-joined; reported, never pooled.
MISJOINED = {"beethoven-sym5-mvt1-984073-p4", "beethoven-sym5-mvt1-575951-p4"}


def _deref(rows: dict, row: dict, key: str):
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def printed_names(rows: dict, rid: str) -> list[str] | None:
    """The hand-read printed label of each staff, system 1 / the page lineup."""
    row = rows[rid]
    staves = _deref(rows, row, "staves")
    if isinstance(staves, list):
        return [str(s.get("name") or "") for s in staves]
    sap = _deref(rows, row, "systems_as_printed")
    if isinstance(sap, dict) and isinstance(sap.get("system_1"), list):
        return [str(s.get("name") or "") for s in sap["system_1"]]
    cond = (row.get("condensation") or {}).get("staves_as_printed")
    if isinstance(cond, list):
        return [str(s.get("name") or "") for s in cond if s.get("lines") == 5]
    return None


def family_of(name: str) -> str | None:
    m = lookup(name)
    return m.instrument.family if m else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(FIXTURES))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    fx = Path(args.fixtures)

    rows_meta = {r["row_id"]: r for r in json.loads(WORKS.read_text())["rows"]}
    report: dict = {}

    print("COVERAGE — what carries bracket evidence at all\n")
    print(f"{'row':<34} {'staves':>6} {'blocks':>6} {'sizes':>16} "
          f"{'families named':>15}")
    for p in sorted(fx.glob(f"*{SUFFIX}")):
        rid = p.name[:-len(SUFFIX)]
        result = json.loads(p.read_text())
        ref = (result.get("contextual") or {}).get("reference")
        if not ref:
            report[rid] = {"blocks": None,
                           "reason": "contextual carries no reference"}
            print(f"{rid:<34} {'—':>6} {'— none':>6}")
            continue
        blocks: dict[int, list[int]] = {}
        for entry in ref:
            blocks.setdefault(entry.get("group", 0), []).append(entry["slot"])
        names = printed_names(rows_meta, rid)
        fams = [family_of(n) for n in names] if names else None
        report[rid] = {"n_staves": len(ref), "n_blocks": len(blocks),
                       "sizes": [len(v) for _, v in sorted(blocks.items())],
                       "printed": names,
                       "families": fams,
                       "blocks": {str(k): v for k, v in sorted(blocks.items())}}
        named = sum(1 for f in (fams or []) if f)
        print(f"{rid:<34} {len(ref):>6} {len(blocks):>6} "
              f"{str(report[rid]['sizes']):>16} "
              f"{(f'{named}/{len(fams)}' if fams else '— no map'):>15}")

    with_blocks = [r for r, v in report.items() if v.get("blocks")]
    print(f"\nrows carrying bracket blocks: {len(with_blocks)}/{len(report)}")
    print(f"staves in a block: "
          f"{sum(report[r]['n_staves'] for r in with_blocks)}")

    # ── purity: does a block ever mix families? ──────────────────────────
    print("\n\nPURITY — does a block ever hold two families?\n")
    print(f"{'row':<34} {'blocks':>6} {'pure':>5} {'mixed':>5}   mixed detail")
    pooled = Counter()
    for rid in sorted(with_blocks):
        rec = report[rid]
        fams = rec["families"]
        if not fams:
            print(f"{rid:<34} {rec['n_blocks']:>6}   — no hand-read map")
            continue
        pure = mixed = 0
        detail = []
        for gid, slots in sorted(rec["blocks"].items()):
            seen = {fams[s] for s in slots if s < len(fams) and fams[s]}
            if len(seen) <= 1:
                pure += 1
            else:
                mixed += 1
                detail.append(f"g{gid}:{'+'.join(sorted(seen))}")
        rec["pure_blocks"], rec["mixed_blocks"] = pure, mixed
        tag = "  (MIS-JOINED SLOTS)" if rid in MISJOINED else ""
        if rid not in MISJOINED:
            pooled["pure"] += pure
            pooled["mixed"] += mixed
        print(f"{rid:<34} {rec['n_blocks']:>6} {pure:>5} {mixed:>5}   "
              f"{', '.join(detail) or '—'}{tag}")

    tot = pooled["pure"] + pooled["mixed"]
    print(f"\npooled (mis-joined rows excluded): {pooled['pure']}/{tot} blocks "
          f"pure ({pooled['pure']/max(1,tot):.3f})")

    # ── recall: how many true family boundaries are block boundaries? ────
    print("\n\nRECALL — are true family boundaries found as block boundaries?\n")
    print(f"{'row':<34} {'true bnds':>9} {'found':>6} {'extra':>6}")
    rec_pool = Counter()
    for rid in sorted(with_blocks):
        rec = report[rid]
        fams = rec["families"]
        if not fams:
            continue
        n = min(rec["n_staves"], len(fams))
        slot_group = {e: g for g, ss in rec["blocks"].items() for e in ss}
        true_b = {i for i in range(1, n)
                  if fams[i] and fams[i - 1] and fams[i] != fams[i - 1]}
        blk_b = {i for i in range(1, n)
                 if slot_group.get(i) != slot_group.get(i - 1)}
        found, extra = true_b & blk_b, blk_b - true_b
        rec["true_boundaries"], rec["found"] = len(true_b), len(found)
        if rid not in MISJOINED:
            rec_pool["true"] += len(true_b)
            rec_pool["found"] += len(found)
            rec_pool["extra"] += len(extra)
        tag = "  (MIS-JOINED SLOTS)" if rid in MISJOINED else ""
        print(f"{rid:<34} {len(true_b):>9} {len(found):>6} {len(extra):>6}{tag}")
    print(f"\npooled (mis-joined excluded): recall "
          f"{rec_pool['found']}/{rec_pool['true']} "
          f"({rec_pool['found']/max(1,rec_pool['true']):.3f}), "
          f"{rec_pool['extra']} block boundaries that are not family boundaries")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = HERE / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
