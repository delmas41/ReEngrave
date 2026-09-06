"""Score the scan gate against a PAGE-NORMALISED truth, beside the raw one.

    python3 benchmarks/omr-headline-validity-2026-09/normalised_arm.py
    python3 benchmarks/omr-headline-validity-2026-09/normalised_arm.py --rows dvorak-sym9-mvt1-405834-p5

Both columns are measured HERE, on one tree, in one musicdiff batch, from the
same prediction files — because a ratio between a raw number from one tree and
a normalised number from another is not an attribution. Every scored file's
sha256 goes into the output.

WHAT EACH COLUMN IS.

  raw          the prediction against `fixtures/<row>.truth.musicxml`, the
               reference encoding trimmed to the page's measures. This is the
               HEADLINE and it stays the headline. Re-computed here rather than
               read out of `results-*.json`, so drift is visible.

  normalised   the same prediction against a derived truth whose PARTS are the
               page's printed STAVES (`page_normalise.py`, driven by the
               hand-read `staves` map in `works.json`).

  ⚠️ THEY ARE DIFFERENT BENCHMARK ERAS. OMR-NED is symmetric, so merging parts
  moves the denominator too. The delta is STRUCTURAL CHARGE REMOVED — the
  metric ceasing to bill us for a convention — and is NOT pipeline improvement.

DVORAK IS THE CONTROL AND MUST BE A NO-OP. Its print is the one 1:1
part-per-staff pair in the corpus, so a 15-into-15 map asks the transform to
change nothing. If its score moves, the transform is distorting the truth and
no other row's number means anything.

A ROW WITH NO HAND MAP IS NOT NORMALISED. It is listed as `un-normalised` with
its reason. Nothing is inferred from the encoding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

import page_normalise  # noqa: E402   (lives beside scan_eval.py)
from tools.omr import omr_ned as omr_ned_mod  # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"
WORKS = SCAN / "works.json"
DERIVED = BENCH / "derived-truth"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def git_head() -> str:
    out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True)
    return out.stdout.strip() or "unknown"


def load_rows() -> list[dict]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        for key in ("staves", "condensation"):
            v = row.get(key)
            if isinstance(v, str) and v.startswith("same-as:"):
                row[key] = by_id[v.split(":", 1)[1]][key]
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--tag", default="..graft09")
    ap.add_argument("--out", default=str(BENCH / "results-normalised-arm.json"))
    args = ap.parse_args(argv)

    rows = load_rows()
    if args.rows:
        want = set(args.rows)
        rows = [r for r in rows if r["row_id"] in want]

    pairs: list[tuple] = []
    entries: list[dict] = []
    skipped: list[dict] = []

    for row in rows:
        rid = row["row_id"]
        truth = FIXTURES / f"{rid}.truth.musicxml"
        pred = FIXTURES / f"{rid}{args.tag}.omr.musicxml"
        if not truth.is_file() or not pred.is_file():
            skipped.append({"row_id": rid, "reason": "no fixture on disk "
                            f"(truth={truth.is_file()}, pred={pred.is_file()})"})
            continue
        entry = {"row_id": rid, "work_id": row["work_id"],
                 "pooled": row.get("pooled", True),
                 "sha": {"truth": sha(truth), "pred": sha(pred)}}
        try:
            norm_xml = DERIVED / f"{rid}.page-normalised.musicxml"
            report = page_normalise.write(
                truth, row.get("staves"), norm_xml,
                source_reference=row["reference"]["catalog_path"])
            entry["normalised"] = True
            entry["transform"] = {
                "version": report["transform_version"],
                "n_source_parts": report["n_source_parts"],
                "n_output_parts": report["n_output_parts"],
                "measure_census": report["measure_census"],
                "exact_duplication_share": report["exact_duplication_share"],
                "divisi_share": report["divisi_share"],
            }
            entry["sha"]["normalised_truth"] = sha(norm_xml)
            pairs.append((f"{rid}|norm", pred, norm_xml))
        except page_normalise.NoHandMap as exc:
            entry["normalised"] = False
            entry["not_normalised_because"] = str(exc)
        pairs.append((f"{rid}|raw", pred, truth))
        entries.append(entry)

    if not pairs:
        print("nothing to score", file=sys.stderr)
        return 1

    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    by_name = {p["name"]: p for p in scored.get("pairs", [])}
    for e in entries:
        e["raw"] = by_name.get(f"{e['row_id']}|raw")
        if e["normalised"]:
            e["norm"] = by_name.get(f"{e['row_id']}|norm")

    def pool(key: str, rows_: list[dict]) -> dict:
        ed = ts = ps = 0
        cats: dict[str, int] = {}
        for e in rows_:
            n = e.get(key)
            if not n:
                return {}
            ed += n["omr_ed"]
            ts += n["truth_symbols"]
            ps += n["pred_symbols"]
            for k, v in (n.get("categories") or {}).items():
                cats[k] = cats.get(k, 0) + v
        return {"omr_ned": ed / (ts + ps) if (ts + ps) else None, "omr_ed": ed,
                "truth_symbols": ts, "pred_symbols": ps, "categories": cats,
                "n_rows": len(rows_)}

    poolable = [e for e in entries if e.get("pooled", True)]
    normalisable = [e for e in poolable if e["normalised"]]

    doc = {
        "generated_by": "benchmarks/omr-headline-validity-2026-09/normalised_arm.py",
        "git_head": git_head(),
        "tag": args.tag,
        "transform_version": page_normalise.TRANSFORM_VERSION,
        "merge_convention": page_normalise.MERGE_CONVENTION,
        "headline_is": "the RAW column. The normalised column is a SEPARATE "
                       "benchmark era and may not be differenced against any "
                       "figure measured on the un-normalised truth.",
        "delta_means": "STRUCTURAL CHARGE REMOVED — the metric ceasing to bill "
                       "a printing convention — NOT pipeline improvement.",
        "coverage": {
            "n_rows_scored": len(entries),
            "n_normalised": len(normalisable),
            "n_un_normalised": len(poolable) - len(normalisable),
            "un_normalised_rows": [e["row_id"] for e in poolable
                                   if not e["normalised"]],
        },
        "skipped_no_fixture": skipped,
        "pooled_over_normalisable_rows_only": {
            "raw": pool("raw", normalisable),
            "normalised": pool("norm", normalisable),
        },
        "pooled_raw_over_all_scored_rows": pool("raw", poolable),
        "rows": entries,
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    hdr = (f"{'row':40s} {'raw NED':>8s} {'raw ed':>7s} | {'norm NED':>8s} "
           f"{'norm ed':>8s} | {'d edits':>8s} {'divisi':>7s}")
    print(hdr)
    print("-" * len(hdr))
    for e in entries:
        raw = e.get("raw") or {}
        nm = e.get("norm")
        if nm:
            d = nm["omr_ed"] - raw.get("omr_ed", 0)
            print(f"{e['row_id']:40s} {raw.get('omr_ned', 0):>8.4f} "
                  f"{raw.get('omr_ed', 0):>7d} | {nm['omr_ned']:>8.4f} "
                  f"{nm['omr_ed']:>8d} | {d:>+8d} "
                  f"{e['transform']['divisi_share']:>7.3f}")
        else:
            print(f"{e['row_id']:40s} {raw.get('omr_ned', 0):>8.4f} "
                  f"{raw.get('omr_ed', 0):>7d} | {'—':>8s} {'—':>8s} | "
                  f"{'UN-NORMALISED':>8s}")
    print()
    pr = doc["pooled_over_normalisable_rows_only"]["raw"]
    pn_ = doc["pooled_over_normalisable_rows_only"]["normalised"]
    if pr and pn_:
        print(f"pooled over the {len(normalisable)} NORMALISABLE rows only")
        print(f"  raw        {pr['omr_ned']:.4f}  {pr['omr_ed']:>6d} edits  "
              f"(entire staff {pr['categories'].get('entire staff insert/delete', 0)})")
        print(f"  normalised {pn_['omr_ned']:.4f}  {pn_['omr_ed']:>6d} edits  "
              f"(entire staff {pn_['categories'].get('entire staff insert/delete', 0)})")
        print(f"  ⚠️  {pr['omr_ed'] - pn_['omr_ed']:+d} edits is STRUCTURAL "
              f"CHARGE REMOVED, not improvement; the two columns are "
              f"different benchmark eras.")
    print(f"\nun-normalised rows ({doc['coverage']['n_un_normalised']}): "
          + (", ".join(doc["coverage"]["un_normalised_rows"]) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
