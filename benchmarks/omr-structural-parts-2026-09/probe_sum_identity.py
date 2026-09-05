"""The sum identity: do the assigned players account for the work's parts?

Every over-count Phase 2 measured has ONE cause — the DIVISOR is too small,
because a staff's instrument was mis-read and the dossier's parts are then
divided over fewer staves than the page prints. Brahms's `4 Horner in Es 3./4.`
reads as Trumpet, so 4 horn parts land on 1 staff and the truth is 2.

The check proposed for it is a structural identity rather than a rule about
horns: **the players assigned across a system must account for the work's
parts**. Its two anchors are UNCORRUPTED — `n_parts` is a fact of the dossier
and the staff count is a fact of the page — even though what it checks is the
corrupted assignment. That is what makes it a detector of the corruption rather
than another consumer of it.

⚠️ IT IS ALSO THE DIAGNOSTIC THAT DECIDES PHASE 3. `mahler-sym5-mvt1-local-p3`,
`p4` and `p5` regress under the dossier arm (+233 / +660 / +238) and have no
hand-verified map, so two hypotheses share one symptom: either the COUNTS are
wrong there, or the counts are right and DUPLICATION is what fails. The sum
separates them without a map. Sum holds -> counts are right, the residue is
duplication, which is Phase 3's target. Sum breaks -> the counts are wrong and
the gate should abstain.

TWO GATES ARE MEASURED, both structural, neither tuned:

  system   the system's assigned players must equal the dossier's `n_parts`;
           the whole system abstains where they do not.
  instr    each instrument's assigned total must equal its own dossier part
           count; only that instrument abstains.

⚠️ A page SUPPRESSES TACET STAVES, so a system printing fewer staves than the
work has sections cannot sum to `n_parts` however correct its counts are. That
is a known cost of the strict gate, not a defect in it — it is reported, not
patched around. If a gate starts needing an exception, that is a result.

⚠️ CEILING / REAL-USE. Dossiers are generated from the same Gradus MusicXML the
scan benchmark scores against. Every figure here is a labelled ceiling/real-use
arm and never a benchmark figure.

FIXTURE PROVENANCE. 20-row transcriptions from
`.claude/worktrees/reconciliation/benchmarks/omr-scan-e2e-2026-09/fixtures/`,
suffix `.reconciliation.omr.json`. The main checkout's `fixtures/` still holds
the ELEVEN-row era's `.restamp-composed` set.

    python3 benchmarks/omr-structural-parts-2026-09/probe_sum_identity.py --json sum-identity.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("dc", HERE / "dossier_counts.py")
dc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dc)

SUFFIX = ".reconciliation.omr.json"


def assigned_for_system(system: dict, parts: Counter) -> tuple[list[dict], int,
                                                              Counter]:
    """Per-staff records, the system's assigned total, and it by instrument.

    An ABSTAINED staff still contributes 1 — it is emitted as one part — so the
    total is what the exporter would actually write, which is the quantity the
    identity is about.
    """
    recs = dc.counts_for_system(system, parts)
    total = sum(r["players"] for r in recs)
    by_instr: Counter = Counter()
    for r in recs:
        if r["instrument"]:
            by_instr[r["instrument"]] += r["players"]
    return recs, total, by_instr


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(dc.DEFAULT_FIXTURES))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    fx = Path(args.fixtures)

    report: dict = {}
    print("THE SUM, PER SYSTEM\n")
    print(f"{'row':<34} {'sys':>3} {'staves':>6} {'assigned':>8} "
          f"{'n_parts':>7} {'holds':>6}   instruments over their part count")
    for p in sorted(fx.glob(f"*{SUFFIX}")):
        rid = p.name[:-len(SUFFIX)]
        dos_id = dc.dossier_for(rid)
        if dos_id is None:
            print(f"{rid:<34} {'—':>3} {'—':>6} {'—':>8} {'— no dossier':>7}")
            report[rid] = {"dossier": None}
            continue
        dossier = json.loads((dc.DOSSIERS / f"{dos_id}.json").read_text())
        parts, _ = dc.parts_by_instrument(dossier)
        n_parts = int(dossier.get("n_parts") or len(dossier.get("parts", [])))
        result = json.loads(p.read_text())
        systems = [s for pg in result.get("pages", [])
                   for s in pg.get("systems", []) if s.get("staves")]
        rows = []
        for si, system in enumerate(systems):
            recs, total, by_instr = assigned_for_system(system, parts)
            over = {k: (v, parts[k]) for k, v in by_instr.items()
                    if v > parts.get(k, 0)}
            holds = total == n_parts
            rows.append({"system": si, "staves": len(recs), "assigned": total,
                         "n_parts": n_parts, "sum_holds": holds,
                         "over_instruments": over,
                         "instr_gate_abstains": sorted(over)})
            print(f"{rid:<34} {si:>3} {len(recs):>6} {total:>8} {n_parts:>7} "
                  f"{('yes' if holds else 'NO'):>6}   "
                  f"{', '.join(f'{k} {v[0]}>{v[1]}' for k, v in over.items()) or '—'}")
        report[rid] = {"dossier": dos_id, "n_parts": n_parts, "systems": rows}

    # ── the two gates, as coverage ───────────────────────────────────────
    print("\n\nWHAT EACH GATE SWITCHES OFF\n")
    print(f"{'row':<34} {'system gate':>12} {'instr gate':>28}")
    for rid, rec in sorted(report.items()):
        if not rec.get("dossier"):
            print(f"{rid:<34} {'— no dossier':>12}")
            continue
        sysoff = [str(r["system"]) for r in rec["systems"] if not r["sum_holds"]]
        instroff = sorted({i for r in rec["systems"]
                           for i in r["instr_gate_abstains"]})
        print(f"{rid:<34} "
              f"{('abstains sys ' + ','.join(sysoff)) if sysoff else 'passes':>12} "
              f"{(', '.join(instroff) or 'passes'):>28}")

    # ── the Mahler verdict ───────────────────────────────────────────────
    print("\n\nTHE MAHLER VERDICT — counts, or duplication?\n")
    for rid in sorted(report):
        if not rid.startswith("mahler"):
            continue
        rec = report[rid]
        for r in rec["systems"]:
            verdict = ("counts ACCOUNT for the work -> the residue is "
                       "DUPLICATION (Phase 3)" if r["sum_holds"] else
                       "counts do NOT account for the work -> the COUNTS are "
                       "wrong here")
            print(f"  {rid:<32} sys {r['system']}  assigned {r['assigned']:>3} "
                  f"vs n_parts {r['n_parts']:>3}   {verdict}")

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = HERE / dest
        dest.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
