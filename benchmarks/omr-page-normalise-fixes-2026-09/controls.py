"""The controls for the `page_normalise` fixes. Two of them CANNOT improve.

`page_normalise` builds a DERIVED GROUND TRUTH, so a bug in it does not make a
number worse — it makes every number better while being wrong. That has already
happened twice on this module (dropped spanners; a dropped part), and both were
caught by a control rather than by the score. So every change to it is checked
against arms that must move by EXACTLY ZERO:

  1. ⚠️ THE DVOŘÁK ROWS. p5/p6/p7 carry a hand-read map of 15 parts into 15
     printed staves — no condensed staff anywhere on the page — so the
     transform is asked to change nothing and the delta must be 0 to the edit.
     A non-zero delta there means the transform distorts a truth it was told to
     leave alone, and no other row's number would mean anything.

  2. THE ALREADY-MAPPED SCAN ROWS (Beethoven ×8, Brahms ×4). These DO condense,
     so their delta is not zero — but it must be IDENTICAL to what the shipped
     module produced before the fix, because none of the three faults is
     reachable on them. This is the arm that proves the fix is narrow.

  3. THE FIVE UNMAPPED ROWS, under the candidate maps of
     `benchmarks/omr-staves-map-completion-2026-09/`, scored with the FIXED
     module and no monkeypatch. These must reproduce that benchmark's
     `price-maps.json` to the edit — i.e. the fix in the module and the
     probe-only patch beside it are the same transform.

⚠️ EVERY COLUMN HERE IS SCORED IN ONE musicdiff BATCH ON ONE TREE, from the
canonical run's own predictions (`.reconciliation`). Nothing is re-transcribed,
so this measures the TRANSFORM and only the transform.

⚠️ A NORMALISED FIGURE IS A DIFFERENT BENCHMARK ERA (`page_normalise` rule 5).
The `raw -> norm` delta is STRUCTURAL CHARGE REMOVED, never improvement, and it
may not be differenced against the recorded 20-row 0.8444.

    python3 benchmarks/omr-page-normalise-fixes-2026-09/controls.py
    python3 benchmarks/omr-page-normalise-fixes-2026-09/controls.py --rows dvorak-sym9-mvt1-405834-p5
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-staves-map-completion-2026-09"))

import page_normalise                              # noqa: E402
from tools.omr import omr_ned as omr_ned_mod       # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
WORKS = ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"
PRICED = (ROOT / "benchmarks/omr-staves-map-completion-2026-09"
          / "price-maps.json")
OUT = HERE / "controls.json"

#: rows whose hand map merges NOTHING — the arm that cannot improve.
IDENTITY_CONTROL = ("dvorak-sym9-mvt1-405834-p5",
                    "dvorak-sym9-mvt1-405834-p6",
                    "dvorak-sym9-mvt1-405834-p7")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def works_rows() -> dict:
    doc = json.loads(WORKS.read_text())
    return {r["row_id"]: r for r in doc["rows"]}


def hand_map(rows: dict, row_id: str):
    v = rows[row_id].get("staves")
    if isinstance(v, str) and v.startswith("same-as:"):
        v = rows[v.split(":", 1)[1]]["staves"]
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--no-candidates", action="store_true",
                    help="skip arm 3 (the five unmapped rows)")
    ap.add_argument("--out", default=str(OUT),
                    help="where to write the record (the pre-fix arm is run "
                         "with the module stashed and its own --out)")
    args = ap.parse_args(argv)
    out_path = Path(args.out)

    rows = works_rows()
    plan: list[tuple[str, list, str]] = []
    for rid, row in rows.items():
        m = hand_map(rows, rid)
        if not m:
            continue
        kind = ("identity control (no condensed staff)"
                if rid in IDENTITY_CONTROL else "already-mapped row")
        plan.append((rid, m, kind))

    if not args.no_candidates:
        import candidate_maps
        for rid in candidate_maps.CANDIDATES:
            plan.append((rid, candidate_maps.flat(rid), "candidate map"))

    if args.rows:
        plan = [p for p in plan if p[0] in set(args.rows)]

    tmp = Path(tempfile.mkdtemp(prefix="page-normalise-controls-"))
    pairs, entries = [], []
    for rid, smap, kind in plan:
        truth = REC / f"{rid}.truth.musicxml"
        pred = REC / f"{rid}.reconciliation.omr.musicxml"
        if not truth.is_file() or not pred.is_file():
            print(f"SKIP {rid}: missing fixture", file=sys.stderr)
            continue
        norm = tmp / f"{rid}.page-normalised.musicxml"
        rep = page_normalise.write(truth, smap, norm,
                                   source_reference=str(truth))
        entries.append({
            "row_id": rid, "arm": kind,
            "sha": {"truth": sha(truth), "pred": sha(pred),
                    "normalised_truth": sha(norm)},
            "n_source_parts": rep["n_source_parts"],
            "n_output_parts": rep["n_output_parts"],
            "measure_census": rep["measure_census"],
        })
        pairs.append((f"{rid}|raw", pred, truth))
        pairs.append((f"{rid}|norm", pred, norm))

    # ⚠️ SCORED IN CHUNKS, ONE SUBPROCESS EACH. `score_batch` carries a
    # single wall-clock timeout for the whole job, and the Mahler pages are
    # slow enough that one batch of every row times out — which reports as
    # a scorer error, not as a wrong number, but costs the run.
    by = {}
    for i in range(0, len(pairs), 6):
        scored = omr_ned_mod.score_batch(pairs[i:i + 6], detail="AllObjects",
                                         timeout_s=3600.0)
        by.update({p["name"]: p for p in scored.get("pairs", [])})
    for e in entries:
        e["raw"] = by.get(f"{e['row_id']}|raw")
        e["norm"] = by.get(f"{e['row_id']}|norm")
        e["delta_edits"] = e["norm"]["omr_ed"] - e["raw"]["omr_ed"]
        e["delta_entire_staff"] = (
            e["norm"]["categories"].get("entire staff insert/delete", 0)
            - e["raw"]["categories"].get("entire staff insert/delete", 0))

    # ---------------------------------------------------------- the verdicts
    failures = []
    for e in entries:
        if e["arm"].startswith("identity control") and e["delta_edits"] != 0:
            failures.append(f"{e['row_id']} moved by {e['delta_edits']:+d} "
                            f"edits and CANNOT — it merges nothing")

    # arm 3: reproduce the completion benchmark's priced figures exactly
    reproduced = None
    if PRICED.is_file():
        priced = {r["row_id"]: r for r in json.loads(PRICED.read_text())["rows"]
                  if r["map_kind"] == "candidate"}
        reproduced = []
        for e in entries:
            p = priced.get(e["row_id"])
            if p is None or e["arm"] != "candidate map":
                continue
            same = (p["norm"]["omr_ed"] == e["norm"]["omr_ed"]
                    and p["raw"]["omr_ed"] == e["raw"]["omr_ed"])
            reproduced.append({"row_id": e["row_id"], "same": same,
                               "probe_patched_norm_ed": p["norm"]["omr_ed"],
                               "fixed_module_norm_ed": e["norm"]["omr_ed"]})
            if not same:
                failures.append(
                    f"{e['row_id']}: the fixed module scores "
                    f"{e['norm']['omr_ed']} where the probe patch scored "
                    f"{p['norm']['omr_ed']} — they are not the same transform")

    doc = {
        "generated_by": "benchmarks/omr-page-normalise-fixes-2026-09/controls.py",
        "git_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse",
                                    "--short", "HEAD"], capture_output=True,
                                   text=True).stdout.strip(),
        "transform_version": page_normalise.TRANSFORM_VERSION,
        "prediction_tag": "reconciliation (the canonical 20-row baseline run)",
        "warning": ("The normalised column is a DIFFERENT BENCHMARK ERA. The "
                    "delta is structural charge removed, not improvement."),
        "identity_control_rows": list(IDENTITY_CONTROL),
        "reproduces_price_maps": reproduced,
        "failures": failures,
        "verdict": "PASS" if not failures else "FAIL",
        "rows": entries,
    }
    out_path.write_text(json.dumps(doc, indent=1) + "\n")

    hdr = (f"{'row':34s} {'raw ed':>7s} {'norm ed':>8s} {'d ed':>7s} "
           f"{'d ES':>7s}  arm")
    print(hdr); print("-" * len(hdr))
    for e in sorted(entries, key=lambda x: (x["arm"], x["row_id"])):
        print(f"{e['row_id']:34s} {e['raw']['omr_ed']:>7d} "
              f"{e['norm']['omr_ed']:>8d} {e['delta_edits']:>+7d} "
              f"{e['delta_entire_staff']:>+7d}  {e['arm']}")
    print()
    for f in failures:
        print("FAIL:", f)
    print(doc["verdict"], "-- wrote", out_path)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
