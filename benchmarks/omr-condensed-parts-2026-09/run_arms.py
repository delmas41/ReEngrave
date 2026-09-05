"""Price emitting one part per REFERENCE part from a condensed printed staff.

Re-exports the transcriptions the scan benchmark already committed
(`fixtures/*.restamp-composed.omr.json`) under each arm and scores them with
musicdiff. `OMR_CONDENSED_PARTS` changes `export.to_musicxml` and nothing
upstream, so the two arms differ in the exporter and in nothing else — no
detector time is spent and the A/B is exact. Same method as
`benchmarks/omr-staff-structure-2026-09/run_arms.py`.

ARMS

  baseline   flag off — one part per printed staff, today's behaviour.
  oracle     the split count comes from `works.json`'s hand-verified
             `staves[i].parts`. ⚠️ THAT IS THE ANSWER KEY. This arm is not
             shippable and is not proposed as such: it measures the CEILING of
             a perfect split, so the inference is only worth building if the
             ceiling is worth having.
  label      the split count is INFERRED from the printed margin label, which
             is what a shippable rule could see.

  --stitch   runs every arm again with `OMR_SLOT_STITCH=1`, to see whether the
             two structural changes compose.

    export OMRNED_PYTHON=/Users/seanjohnson/Desktop/ReEngrave/.venv-omrned/bin/python
    python3 benchmarks/omr-condensed-parts-2026-09/run_arms.py --json arms.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.omr import omr_ned  # noqa: E402
from tools.omr.condensed_parts import players_for_label  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402

ROWS = [
    "beethoven-sym5-mvt1-984073-p1", "beethoven-sym5-mvt1-984073-p2",
    "beethoven-sym5-mvt1-575951-p1", "beethoven-sym5-mvt1-575951-p2",
    "dvorak-sym9-mvt1-405834-p5", "dvorak-sym9-mvt1-405834-p6",
    "brahms-sym1-mvt1-317803-p1", "brahms-sym1-mvt1-317803-p2",
    "mahler-sym5-mvt1-local-p2", "mahler-sym5-mvt1-local-p3",
    "bach-brandenburg3-mvt1-468678-p1",
]
ES = "entire staff insert/delete"
EM = "entire measure insert/delete"


# ── the answer key, for the oracle arm only ──────────────────────────────────
def oracle_map(works: dict) -> dict[str, list[int]]:
    """row_id -> per printed staff, how many reference parts it carries.

    Abstains (absent key) where `works.json` holds no positional map. Those
    rows then run identically to baseline in every arm, which is recorded
    rather than hidden.
    """
    rows = {r["row_id"]: r for r in works["rows"]}
    out: dict[str, list[int]] = {}
    for rid, row in rows.items():
        staves = row.get("staves")
        if isinstance(staves, str):
            staves = rows.get(staves.split(":", 1)[-1].strip(), {}).get("staves")
        if staves and not isinstance(staves, str):
            out[rid] = [max(1, len(s.get("parts") or [1])) for s in staves]
            continue
        # Brahms p2 carries its map per system; system 1 is the full lineup.
        sap = row.get("systems_as_printed")
        if sap and sap.get("system_1"):
            out[rid] = [max(1, len(s.get("parts") or [1]))
                        for s in sap["system_1"]]
            continue
        # Mahler p2 keeps its map beside the one-line percussion staves the
        # five-line detector cannot find; only the five-line entries pair.
        cond = row.get("condensation", {}).get("staves_as_printed")
        if cond:
            out[rid] = [max(1, len(s.get("parts") or [1]))
                        for s in cond if s.get("lines") == 5]
    return out


def printed_labels(works: dict) -> dict[str, list[str]]:
    """row_id -> the printed margin label of each staff, as hand-read.

    Used by the `label_ideal` arm: it prices the RULE with a perfect reader,
    separating the rule's own errors from the OCR's. The shippable path reads
    the same strings off the page through Surya.
    """
    rows = {r["row_id"]: r for r in works["rows"]}
    out: dict[str, list[str]] = {}
    for rid, row in rows.items():
        staves = row.get("staves")
        if isinstance(staves, str):
            staves = rows.get(staves.split(":", 1)[-1].strip(), {}).get("staves")
        if staves and not isinstance(staves, str):
            out[rid] = [str(s.get("name") or "") for s in staves]
            continue
        sap = row.get("systems_as_printed")
        if sap and sap.get("system_1"):
            out[rid] = [str(s.get("name") or "") for s in sap["system_1"]]
            continue
        cond = row.get("condensation", {}).get("staves_as_printed")
        if cond:
            out[rid] = [str(s.get("name") or "")
                        for s in cond if s.get("lines") == 5]
    return out


def label_map(result: dict) -> list[int]:
    """Per printed staff of the first system, players inferred from the label."""
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            if system.get("staves"):
                return [players_for_label(s.get("instrument_label"),
                                          s.get("instrument"))
                        for s in system["staves"]]
    return []


def inject(result: dict, counts: list[int]) -> int:
    """Write `condensed_parts` onto every staff, by position within its system."""
    n = 0
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            for i, staff in enumerate(system.get("staves", [])):
                if i < len(counts) and counts[i] > 1:
                    staff["condensed_parts"] = counts[i]
                    n += 1
    return n


def export_arm(fixtures: Path, out: Path, tag: str, *, flag: str, stitch: str,
               counts_for) -> dict[str, Path]:
    os.environ["OMR_CONDENSED_PARTS"] = flag
    os.environ["OMR_SLOT_STITCH"] = stitch
    paths = {}
    for row in ROWS:
        src = fixtures / f"{row}.restamp-composed.omr.json"
        result = json.loads(src.read_text())
        if counts_for is not None:
            counts = counts_for(row, result)
            if counts:
                inject(result, counts)
        dst = out / f"{row}.{tag}.musicxml"
        dst.write_text(to_musicxml(result))
        paths[row] = dst
    return paths


def n_parts(path: Path) -> int:
    return path.read_text().count("<score-part ")


def score_arm(name, paths, fixtures, baseline=None, base_paths=None):
    rows = []
    for r in ROWS:
        if baseline is not None and paths[r].read_bytes() == base_paths[r].read_bytes():
            rows.append(dict(baseline[ROWS.index(r)], arm=name, unchanged=True))
            continue
        s = omr_ned.score_pair(pred=paths[r], truth=fixtures / f"{r}.truth.musicxml",
                               name=r)
        cats = s.get("categories", {}) or {}
        rows.append({
            "row": r, "arm": name, "unchanged": False,
            "omr_ned": s["omr_ned"], "omr_ed": s["omr_ed"],
            "es": cats.get(ES, 0), "em": cats.get(EM, 0),
            "parts": n_parts(paths[r]),
        })
    ed = sum(r["omr_ed"] for r in rows)
    sym = sum(r.get("symbols", 0) for r in rows)
    return rows, ed, sym


def pooled(rows, fixtures):
    """Pooled OMR-NED over the arm — recomputed from each row's own totals."""
    num = sum(r["omr_ed"] for r in rows)
    den = sum(r.get("_den", 0) for r in rows)
    return (num / den if den else None), num


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=str(
        ROOT / "benchmarks/omr-scan-e2e-2026-09/fixtures"))
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "out"))
    ap.add_argument("--works", default=str(
        ROOT / "benchmarks/omr-scan-e2e-2026-09/works.json"))
    ap.add_argument("--stitch", action="store_true",
                    help="also run every arm with OMR_SLOT_STITCH=1")
    ap.add_argument("--arms", default="baseline,oracle,label")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    fixtures, out = Path(args.fixtures), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    works = json.loads(Path(args.works).read_text())
    omap = oracle_map(works)
    lmap = printed_labels(works)
    print("oracle map covers:", sorted(omap))
    print("oracle ABSTAINS on:", [r for r in ROWS if r not in omap], "\n")

    # Provenance: a parallel workstream can re-export the fixtures under you.
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    shas = {r: hashlib.sha256(
        (fixtures / f"{r}.restamp-composed.omr.json").read_bytes()).hexdigest()[:16]
        for r in ROWS}

    wanted = args.arms.split(",")
    stitch_modes = ["0", "1"] if args.stitch else ["0"]
    report = {"head": head, "fixture_sha256_16": shas, "arms": {}}

    for stitch in stitch_modes:
        suffix = "+stitch" if stitch == "1" else ""
        base_paths = export_arm(fixtures, out, f"baseline{suffix}",
                                flag="0", stitch=stitch, counts_for=None)
        base_rows, _, _ = score_arm(f"baseline{suffix}", base_paths, fixtures)
        report["arms"][f"baseline{suffix}"] = base_rows

        arm_defs = {
            "oracle": lambda row, res: omap.get(row),
            "label": lambda row, res: label_map(res),
            "label_ideal": lambda row, res: (
                [players_for_label(t) for t in lmap[row]] if row in lmap else None),
            "label_explicit": lambda row, res: (
                [players_for_label(t, tiers=("explicit", "compound"))
                 for t in lmap[row]] if row in lmap else None),
        }
        for arm in wanted:
            if arm == "baseline":
                continue
            paths = export_arm(fixtures, out, f"{arm}{suffix}", flag="1",
                               stitch=stitch, counts_for=arm_defs[arm])
            rows, _, _ = score_arm(f"{arm}{suffix}", paths, fixtures,
                                   baseline=base_rows, base_paths=base_paths)
            report["arms"][f"{arm}{suffix}"] = rows

    # ── report ───────────────────────────────────────────────────────────────
    for name, rows in report["arms"].items():
        ed = sum(r["omr_ed"] for r in rows)
        es = sum(r["es"] for r in rows)
        em = sum(r["em"] for r in rows)
        print(f"\n=== {name}: edits {ed}  ES {es}  EM {em}  "
              f"ES+EM {es + em}")
        for r in rows:
            print(f"   {r['row']:38s} ned {r['omr_ned']:.4f} ed {r['omr_ed']:6d} "
                  f"ES {r['es']:5d} EM {r['em']:5d} parts {r['parts']:3d}"
                  f"{'  (unchanged)' if r.get('unchanged') else ''}")

    base = report["arms"]["baseline"]
    print("\n\n=== deltas vs baseline (edits; negative is better)")
    for name, rows in report["arms"].items():
        if name == "baseline":
            continue
        d = sum(r["omr_ed"] for r in rows) - sum(r["omr_ed"] for r in base)
        des = sum(r["es"] for r in rows) - sum(r["es"] for r in base)
        dem = sum(r["em"] for r in rows) - sum(r["em"] for r in base)
        print(f"   {name:20s} edits {d:+6d}   ES {des:+6d}   EM {dem:+6d}   "
              f"ES+EM {des + dem:+6d}")

    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
