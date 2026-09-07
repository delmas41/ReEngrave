"""What would a `staves` map be WORTH on the five unmapped scan-gate rows?

Both columns are measured here, on one tree, in one musicdiff batch, from the
same prediction files — the convention `normalised_arm.py` sets, because a
ratio between a number from one tree and a number from another is not an
attribution.

⚠️ THE COLUMNS ARE DIFFERENT BENCHMARK ERAS (`page_normalise` rule 5). The
delta is STRUCTURAL CHARGE REMOVED — the metric ceasing to bill a printing
convention — and is NOT the pipeline improving. It may not be differenced
against the recorded 20-row 0.8444.

⚠️ THE PREDICTIONS ARE THE CANONICAL RUN'S (`.reconciliation`), read from the
reconciliation worktree, which is the artefact `results-reconciliation.json`
(pooled 0.8444) was computed from. Nothing is re-transcribed here, so this
prices the MAP and only the map.

CONTROL: `dvorak-sym9-mvt1-405834-p5` is scored with its own works.json map,
which is 15 parts into 15 staves — the transform asked to change nothing. If
its delta is not 0 the harness is distorting the truth and no other row's
number means anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAIN = Path("/Users/seanjohnson/Desktop/ReEngrave")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))
sys.path.insert(0, str(HERE))

import page_normalise                      # noqa: E402
import candidate_maps                      # noqa: E402
import normalise_patched                   # noqa: E402
from tools.omr import omr_ned as omr_ned_mod   # noqa: E402

REC = (MAIN / ".claude/worktrees/reconciliation/benchmarks"
       "/omr-scan-e2e-2026-09/fixtures")
WORKS = MAIN / "benchmarks/omr-scan-e2e-2026-09/works.json"
DERIVED = HERE / "derived-truth"
OUT = HERE / "price-maps.json"

CONTROL = "dvorak-sym9-mvt1-405834-p5"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def works_map(row_id: str):
    doc = json.loads(WORKS.read_text())
    by_id = {r["row_id"]: r for r in doc["rows"]}
    row = by_id[row_id]
    v = row.get("staves")
    if isinstance(v, str) and v.startswith("same-as:"):
        v = by_id[v.split(":", 1)[1]]["staves"]
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-patch", action="store_true",
                    help="do not apply the probe-only page_normalise patches")
    args = ap.parse_args(argv)
    if not args.no_patch:
        normalise_patched.apply()

    plan = [(rid, candidate_maps.flat(rid), "candidate")
            for rid in candidate_maps.CANDIDATES]
    plan += [(rid, candidate_maps.flat_sorted(rid), "sorted-parts")
             for rid in candidate_maps.CANDIDATES
             if candidate_maps.absent_parts(rid)]
    plan += [(rid, candidate_maps.five_line_only(rid), "diagnostic-fiveline")
             for rid in candidate_maps.CANDIDATES if rid.startswith("mahler")]
    plan.append((CONTROL, works_map(CONTROL), "control (works.json map)"))

    pairs, entries = [], []
    for rid, smap, kind in plan:
        truth = REC / f"{rid}.truth.musicxml"
        pred = REC / f"{rid}.reconciliation.omr.musicxml"
        if not truth.is_file() or not pred.is_file():
            print(f"SKIP {rid}: missing fixture", file=sys.stderr)
            continue
        suffix = {"candidate": "", "control (works.json map)": "",
                  "sorted-parts": ".sorted",
                  "diagnostic-fiveline": ".fiveline"}[kind]
        norm = DERIVED / f"{rid}{suffix}.page-normalised.musicxml"
        report = page_normalise.write(truth, smap, norm)
        entries.append({
            "row_id": rid, "map_kind": kind,
            "sha": {"truth": sha(truth), "pred": sha(pred),
                    "normalised_truth": sha(norm)},
            "transform": {
                "n_source_parts": report["n_source_parts"],
                "n_output_parts": report["n_output_parts"],
                "measure_census": report["measure_census"],
                "exact_duplication_share": report["exact_duplication_share"],
                "divisi_share": report["divisi_share"],
            },
        })
        key = rid + suffix
        pairs.append((f"{key}|raw", pred, truth))
        pairs.append((f"{key}|norm", pred, norm))

    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    by_name = {p["name"]: p for p in scored.get("pairs", [])}
    for e in entries:
        k = e["row_id"] + {"candidate": "", "control (works.json map)": "",
                           "sorted-parts": ".sorted",
                           "diagnostic-fiveline": ".fiveline"}[e["map_kind"]]
        e["raw"] = by_name.get(f"{k}|raw")
        e["norm"] = by_name.get(f"{k}|norm")

    def pool(key, rows_):
        ed = ts = ps = 0
        cats = {}
        for e in rows_:
            n = e[key]
            ed += n["omr_ed"]
            ts += n["truth_symbols"]
            ps += n["pred_symbols"]
            for k, v in (n.get("categories") or {}).items():
                cats[k] = cats.get(k, 0) + v
        return {"omr_ned": ed / (ts + ps) if (ts + ps) else None,
                "omr_ed": ed, "truth_symbols": ts, "pred_symbols": ps,
                "categories": cats, "n_rows": len(rows_)}

    cand = [e for e in entries if e["map_kind"] == "candidate"]
    doc = {
        "generated_by": "benchmarks/omr-staves-map-completion-2026-09/price_maps.py",
        "git_head": subprocess.run(["git", "-C", str(ROOT), "rev-parse",
                                    "--short", "HEAD"], capture_output=True,
                                   text=True).stdout.strip(),
        "prediction_tag": "reconciliation (the canonical 20-row baseline run)",
        "page_normalise_patched": not args.no_patch,
        "warning": ("The normalised column is a DIFFERENT BENCHMARK ERA. The "
                    "delta is structural charge removed, not improvement, and "
                    "may not be differenced against the 20-row 0.8444."),
        "pooled_over_the_five_candidate_rows": {
            "raw": pool("raw", cand), "normalised": pool("norm", cand)},
        "rows": entries,
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")

    hdr = (f"{'row':36s} {'raw NED':>8s} {'raw ed':>7s} {'raw ES':>7s} | "
           f"{'nrm NED':>8s} {'nrm ed':>7s} {'nrm ES':>7s} | {'d ed':>7s} {'d ES':>6s}")
    print(hdr); print("-" * len(hdr))
    for e in entries:
        r, n = e["raw"], e["norm"]
        res = r["categories"].get("entire staff insert/delete", 0)
        nes = n["categories"].get("entire staff insert/delete", 0)
        tag = e["row_id"] + {"candidate": "", "control (works.json map)": "",
                             "sorted-parts": " [sorted]",
                             "diagnostic-fiveline": " [5-line]"}[e["map_kind"]]
        print(f"{tag:44s} {r['omr_ned']:>8.4f} {r['omr_ed']:>7d} "
              f"{res:>7d} | {n['omr_ned']:>8.4f} {n['omr_ed']:>7d} {nes:>7d} | "
              f"{n['omr_ed']-r['omr_ed']:>+7d} {nes-res:>+6d}"
              + ("   <- CONTROL" if e["map_kind"].startswith("control") else ""))
    p = doc["pooled_over_the_five_candidate_rows"]
    print()
    print(f"pooled over the five candidate rows  raw {p['raw']['omr_ned']:.4f} "
          f"/ {p['raw']['omr_ed']} ed  (entire staff "
          f"{p['raw']['categories'].get('entire staff insert/delete', 0)})")
    print(f"                                     nrm {p['normalised']['omr_ned']:.4f} "
          f"/ {p['normalised']['omr_ed']} ed  (entire staff "
          f"{p['normalised']['categories'].get('entire staff insert/delete', 0)})")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
