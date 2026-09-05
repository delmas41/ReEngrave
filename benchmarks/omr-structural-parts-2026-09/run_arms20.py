"""Re-price `OMR_SLOT_STITCH` and `OMR_CONDENSED_PARTS` on the 20-row scan era.

Both flags were priced when the scan benchmark held ELEVEN rows
(`benchmarks/omr-staff-structure-2026-09/FINDINGS.md`,
`benchmarks/omr-condensed-parts-2026-09/FINDINGS.md`). The gate is now twenty
(`benchmarks/omr-scan-e2e-2026-09/results-reconciliation.json`, pooled
0.8443958866 / 74,968). A pooled figure is a property of the row set it pools
over, so neither prior number transfers, and slot stitch in particular rested
its whole cost/benefit case on ONE page.

METHOD, inherited from the two run_arms.py this replaces and not re-decided.
Both flags change `export.to_musicxml` and NOTHING upstream, so the arms are
produced by RE-EXPORTING the transcriptions the 20-row reconciliation run
already committed. The arms differ in the exporter and in nothing else, the A/B
is exact, and no detector time is spent on a shared machine.

⚠️ THE BASELINE IS THIS TREE'S OWN FLAG-OFF EXPORT, not the committed
`results-reconciliation.json` figure. The reconciliation run exported on a
different commit; a re-export on this tree need not be byte-identical to it, so
comparing an arm here to the committed number would attribute the intervening
merges to a flag. The committed figure is still printed, as a drift check.

⚠️ THE `oracle` ARM IS AN ANSWER KEY. Its per-staff split count comes from
`works.json`'s hand-verified `parts` map, which is derived from the same
reference the run is scored against. It measures a CEILING. It is never a
benchmark figure and is never proposed as a default.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-structural-parts-2026-09/run_arms20.py --json arms20.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402

#: The 20-row reconciliation run's transcriptions. They live in the worktree
#: that produced them; `benchmarks/omr-scan-e2e-2026-09/fixtures/` in the main
#: checkout still holds the ELEVEN-row era's `.restamp-composed` set.
DEFAULT_FIXTURES = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/reconciliation"
    "/benchmarks/omr-scan-e2e-2026-09/fixtures")
SUFFIX = ".reconciliation.omr.json"

WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"
RECON = ROOT / "benchmarks/omr-scan-e2e-2026-09/results-reconciliation.json"

ES = "entire staff insert/delete"
EM = "entire measure insert/delete"


# ── the answer key, for the oracle arm only ─────────────────────────────────

def _deref(rows: dict[str, dict], row: dict, key: str) -> Any:
    """`works.json` lets a row say `same-as:<row_id>` for a whole map."""
    val = row.get(key)
    if isinstance(val, str) and val.startswith("same-as:"):
        return rows.get(val.split(":", 1)[1].strip(), {}).get(key)
    return val


def _counts(entries: list[dict]) -> list[int]:
    return [max(1, len(s.get("parts") or [1])) for s in entries]


def oracle_map(works: dict) -> dict[str, dict[int, list[int]]]:
    """row_id -> {system_index: per-staff reference-part count}.

    PER SYSTEM, not per row, because a page's two systems need not print the
    same lineup: Beethoven 5 p.4 counts 11 staves in both systems and they are
    NOT the same eleven (system 1 splits Violoncello from Basso and prints no
    Timpani; system 2 prints Timpani and merges the basses). A single list
    applied by position would inject the wrong count on system 2.

    A row with no map is absent, and then runs identically to baseline in every
    arm — recorded rather than hidden.
    """
    rows = {r["row_id"]: r for r in works["rows"]}
    out: dict[str, dict[int, list[int]]] = {}
    for rid, row in rows.items():
        staves = _deref(rows, row, "staves")
        if isinstance(staves, list):
            # One lineup, applied to every system of the page.
            out[rid] = {-1: _counts(staves)}
            continue
        sap = _deref(rows, row, "systems_as_printed")
        if isinstance(sap, dict):
            per: dict[int, list[int]] = {}
            for k, v in sap.items():
                if k.startswith("system_") and isinstance(v, list):
                    per[int(k.split("_")[1]) - 1] = _counts(v)
            if per:
                out[rid] = per
            continue
        cond = (row.get("condensation") or {}).get("staves_as_printed")
        if isinstance(cond, list):
            # Mahler p2 keeps one-line percussion staves in the map; only the
            # five-line entries can pair with what the detector found.
            out[rid] = {-1: _counts([s for s in cond if s.get("lines") == 5])}
    return out


def inject(result: dict, per_system: dict[int, list[int]]) -> int:
    """Write `condensed_parts` onto each staff, by position within ITS system."""
    n = 0
    idx = 0
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            if not system.get("staves"):
                continue
            counts = per_system.get(idx, per_system.get(-1, []))
            for i, staff in enumerate(system["staves"]):
                if i < len(counts) and counts[i] > 1:
                    staff["condensed_parts"] = counts[i]
                    n += 1
            idx += 1
    return n


# ── arms ────────────────────────────────────────────────────────────────────

ARMS = {
    #  name             SLOT_STITCH  CONDENSED_PARTS  inject the answer key
    "base":            ("0", "0", False),
    "stitch":          ("1", "0", False),
    "condensed_nosrc": ("0", "1", False),   # control: the flag with no evidence
    "oracle":          ("0", "1", True),
    "oracle_stitch":   ("1", "1", True),
}


def export_arm(rows: list[str], fixtures: Path, out: Path, arm: str,
               omap: dict[str, dict[int, list[int]]]) -> dict[str, Path]:
    stitch, cond, use_oracle = ARMS[arm]
    os.environ["OMR_SLOT_STITCH"] = stitch
    os.environ["OMR_CONDENSED_PARTS"] = cond
    paths: dict[str, Path] = {}
    for row in rows:
        result = json.loads((fixtures / f"{row}{SUFFIX}").read_text())
        if use_oracle and row in omap:
            inject(result, omap[row])
        dst = out / f"{row}.{arm}.musicxml"
        dst.write_text(to_musicxml(result))
        paths[row] = dst
    return paths


def n_parts(path: Path) -> int:
    import re
    return len(re.findall(r"<score-part\b", path.read_text()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(DEFAULT_FIXTURES))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    ap.add_argument("--json", default=None)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--rows", default=None, help="comma list; default all 20")
    args = ap.parse_args()

    fixtures, out = Path(args.fixtures), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    arms = [a for a in args.arms.split(",") if a]

    rows = (args.rows.split(",") if args.rows else
            sorted(p.name[:-len(SUFFIX)] for p in fixtures.glob(f"*{SUFFIX}")))
    print(f"{len(rows)} rows from {fixtures}\n")

    omap = oracle_map(json.loads(WORKS.read_text()))
    missing = [r for r in rows if r not in omap]
    print(f"oracle map covers {len(rows) - len(missing)}/{len(rows)} rows; "
          f"no map (runs as baseline in every arm): {missing}\n")

    exported = {a: export_arm(rows, fixtures, out, a, omap) for a in arms}

    # Which arms actually change which rows — the cheap structural answer,
    # before a single musicdiff call.
    base = exported[arms[0]]
    print(f"{'row':<36} " + " ".join(f"{a:>16}" for a in arms))
    for r in rows:
        cells = []
        for a in arms:
            same = exported[a][r].read_bytes() == base[r].read_bytes()
            cells.append(f"{('=' if same else 'CHANGED') + ' p' + str(n_parts(exported[a][r])):>16}")
        print(f"{r:<36} " + " ".join(cells))
    print()

    # ── score ────────────────────────────────────────────────────────────
    results: dict[str, Any] = {}
    cache: dict[str, dict] = {}   # digest -> score, so identical files score once
    import hashlib
    for a in arms:
        rowscores = []
        for r in rows:
            p = exported[a][r]
            dig = hashlib.sha256(p.read_bytes()).hexdigest()
            key = f"{r}:{dig}"
            if key not in cache:
                truth = fixtures / f"{r}.truth.musicxml"
                s = omr_ned.score_pair(pred=p, truth=truth, name=f"{r}.{a}")
                cache[key] = {"omr_ned": s["omr_ned"], "omr_ed": s["omr_ed"],
                              "pred_symbols": s["pred_symbols"],
                              "truth_symbols": s["truth_symbols"],
                              "categories": s.get("categories", {})}
                print(f"  [{a}] {r:<36} ned {s['omr_ned']:.4f}  ed {s['omr_ed']}",
                      flush=True)
            rowscores.append(dict(cache[key], row=r, arm=a,
                                  parts=n_parts(exported[a][r])))
        ed = sum(x["omr_ed"] for x in rowscores)
        den = sum(x["pred_symbols"] + x["truth_symbols"] for x in rowscores)
        results[a] = {"rows": rowscores, "pooled_omr_ed": ed,
                      "denominator": den,
                      "pooled_omr_ned": ed / den if den else 0.0,
                      "ES": sum(x["categories"].get(ES, 0) for x in rowscores),
                      "EM": sum(x["categories"].get(EM, 0) for x in rowscores)}

    # ── report ───────────────────────────────────────────────────────────
    recon = json.loads(RECON.read_text())["pooled"]
    print(f"\ncommitted reconciliation pooled: "
          f"{recon['omr_ned']:.4f} / {recon['omr_ed']} edits   (drift check)")
    print(f"\n{'arm':<18} {'OMR-NED':>9} {'edits':>8} {'Δ vs base':>10} "
          f"{'ES':>7} {'ΔES':>7} {'EM':>7} {'ΔEM':>7}")
    b = results[arms[0]]
    for a in arms:
        rr = results[a]
        print(f"{a:<18} {rr['pooled_omr_ned']:>9.4f} {rr['pooled_omr_ed']:>8} "
              f"{rr['pooled_omr_ed']-b['pooled_omr_ed']:>+10} "
              f"{rr['ES']:>7} {rr['ES']-b['ES']:>+7} "
              f"{rr['EM']:>7} {rr['EM']-b['EM']:>+7}")

    print(f"\nper row, Δ edits vs {arms[0]}")
    print(f"{'row':<36} {'base ed':>8} " + " ".join(f"{a:>16}" for a in arms[1:]))
    for i, r in enumerate(rows):
        cells = []
        for a in arms[1:]:
            d = results[a]["rows"][i]["omr_ed"] - b["rows"][i]["omr_ed"]
            de = (results[a]["rows"][i]["categories"].get(ES, 0)
                  - b["rows"][i]["categories"].get(ES, 0))
            cells.append(f"{d:>+8} ES{de:>+6}")
        print(f"{r:<36} {b['rows'][i]['omr_ed']:>8} " + " ".join(cells))

    if args.json:
        dest = Path(args.json)
        if not dest.is_absolute():
            dest = Path(__file__).resolve().parent / dest
        dest.write_text(json.dumps(
            {"fixtures": str(fixtures), "rows": rows,
             "oracle_missing": missing,
             "committed_reconciliation_pooled": recon,
             "arms": results}, indent=2) + "\n")
        print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
