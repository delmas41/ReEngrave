"""How much of a scanned row's OMR-NED is the condensation CONVENTION?

A printed orchestral score condenses: Beethoven 5 is engraved on twelve staves
and its reference MusicXML has eighteen parts, because Flauti share a staff and
the file does not. `RESULTS.md` measured that as `entire staff insert/delete` —
2676 pooled edits, 29.6% of the whole corpus — and called it a floor rather than
a defect. This arm asks what the floor is actually worth.

    python3 benchmarks/omr-scan-e2e-2026-09/condensation_arm.py
    python3 benchmarks/omr-scan-e2e-2026-09/condensation_arm.py --rows brahms-sym1-mvt1-317803-p1
    python3 benchmarks/omr-scan-e2e-2026-09/condensation_arm.py --sensitivity

It RE-SCORES the predictions already in `fixtures/`. Nothing is transcribed and
no YOLO runs: the only new artefact is a second ground-truth file per row, built
by `music21.stream.Score.partsToVoices` from the same trimmed window, so the
reference's parts are stacked as VOICES on the number of staves the page prints.

  THE ALLOCATION COMES FROM THE PAGE, NOT FROM THE FILE. `works.json`'s `staves`
  list is hand-read off the scan and already says which reference parts each
  printed staff carries; that list IS the `voiceAllocation`, so this script
  derives it rather than restating it. Mahler has no `staves` map (its printed
  percussion cannot be joined positionally to the prediction — see below), so it
  carries the allocation in its own `condensation` block instead.

  THE RAW-TRUTH COLUMN REMAINS THE HEADLINE. This one attributes; it does not
  flatter. A condensed truth is a different truth, and OMR-NED is symmetric, so
  merging parts moves the DENOMINATOR as well as the numerator — read the edit
  counts beside the ratios, exactly as the resolution arm forced.

  DVORAK IS THE CONTROL AND IT MUST BE A NO-OP. Its print is the one 1:1
  part-per-staff pair in the library, so a 15-into-15 allocation asks
  `partsToVoices` to change nothing. If its score moves, the machinery is
  distorting the truth and no other row's number means anything. Measured: the
  file it writes differs from the untouched truth only in music21's randomly
  regenerated instrument ids, and the score is identical to the edit.

WHAT THE CONDENSED COLUMN DOES *NOT* DO. It does not reproduce the printed page.
Two resting parts merged onto one staff keep two stacked whole rests where the
page prints one, and a printed staff the reference has no part for (Mahler's
`Becken / Gr.Trommel von einem geschlagen` line) cannot be created at all. It is
the minimal mechanical removal of the part-count mismatch, and nothing more.

BOTH COLUMNS ARE MEASURED HERE, ON ONE TREE, AND THE BYTES ARE PINNED. The raw
figure is re-computed rather than read out of `results.json`, because the
prediction files are gitignored and a parallel workstream can re-export them
under you — one did, mid-run, on 2026-09-01, moving Dvorak by a single edit. A
ratio between a raw number from one tree and a condensed number from another is
not an attribution. So every scored file's sha256 and the git HEAD go into the
output, and the raw column is re-stated beside RESULTS.md's so any drift is
visible instead of silent.
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

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import omr_ned as omr_ned_mod  # noqa: E402

WORKS = BENCH / "works.json"
FIXTURES = BENCH / "fixtures"
TRIMMER = BENCH / "trim_reference.py"
VENV_PY = ROOT / ".venv-omrned" / "bin" / "python"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def git_head() -> str:
    proc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True)
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain",
                            "tools/"], capture_output=True, text=True)
    head = proc.stdout.strip() or "unknown"
    return head + (" +uncommitted-tools" if dirty.stdout.strip() else "")


def load_rows() -> tuple[dict, list[dict]]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        for key in ("staves", "condensation"):
            value = row.get(key)
            if isinstance(value, str) and value.startswith("same-as:"):
                row[key] = by_id[value.split(":", 1)[1]][key]
    return doc, rows


def allocation(row: dict, *, sensitivity: bool = False) -> tuple[list[list[int]], dict]:
    """(voiceAllocation, provenance) for one row, or ([], reason) to skip.

    Preferred source is the hand-read `staves` map — the same list the note
    recall arm scores against — so the printed-staff→reference-part join is
    stated once. `condensation.staves_as_printed` is the fallback for a row
    whose staff map cannot be a `staves` map.
    """
    cond = row.get("condensation") or {}
    if cond.get("skip"):
        return [], {"skipped": cond["skip"]}

    if sensitivity:
        alt = cond.get("sensitivity_allocation")
        if not alt:
            return [], {"skipped": "no sensitivity_allocation recorded"}
        return [list(g) for g in alt], {
            "source": "condensation.sensitivity_allocation",
            "why": cond.get("sensitivity_why"),
        }

    staves = row.get("staves")
    if isinstance(staves, list) and staves:
        return ([list(s["parts"]) for s in staves],
                {"source": "works.json staves[].parts (hand-read off the scan)",
                 "printed_staff_names": [s["name"] for s in staves]})

    printed = cond.get("staves_as_printed")
    if printed:
        return ([list(s["parts"]) for s in printed if s.get("parts")],
                {"source": "works.json condensation.staves_as_printed",
                 "confidence": cond.get("confidence"),
                 "printed_staff_names": [s["name"] for s in printed]})

    return [], {"skipped": "no printed-staff -> reference-part map for this row"}


def build_condensed(row: dict, alloc: list[list[int]], out: Path,
                    *, force: bool = False) -> dict:
    report_path = out.with_suffix(".json")
    if out.is_file() and report_path.is_file() and not force:
        return json.loads(report_path.read_text())
    ref = library_root() / row["reference"]["catalog_path"]
    win = row["window"]
    proc = subprocess.run(
        [str(VENV_PY), str(TRIMMER), "--source", str(ref),
         "--first", str(win["first_ref_measure"]),
         "--last", str(win["last_ref_measure"]),
         "--merge-parts", json.dumps(alloc),
         "--out", str(out)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"{row['row_id']}: condensed trim failed\n"
                         f"{proc.stderr[-2000:]}")
    report = json.loads(proc.stdout)
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--force", action="store_true",
                    help="rebuild the condensed truths even if they exist")
    ap.add_argument("--sensitivity", action="store_true",
                    help="use condensation.sensitivity_allocation where a row "
                         "has one — prices the mapping's own ambiguity")
    ap.add_argument("--out", type=Path,
                    default=BENCH / "results-condensation-arm.json")
    ap.add_argument("--detail", default="AllObjects")
    args = ap.parse_args(argv)

    _, rows = load_rows()
    wanted = args.rows or [r["row_id"] for r in rows]
    selected = [r for r in rows if r["row_id"] in wanted]

    raw_pairs, con_pairs, meta = [], [], {}
    for row in selected:
        rid = row["row_id"]
        pred = FIXTURES / f"{rid}.omr.musicxml"
        truth = FIXTURES / f"{rid}.truth.musicxml"
        if not pred.is_file() or not truth.is_file():
            print(f"{rid}: SKIPPED — no prediction/truth in fixtures/ "
                  f"(run scan_eval.py first)", file=sys.stderr)
            continue
        alloc, prov = allocation(row, sensitivity=args.sensitivity)
        if not alloc:
            print(f"{rid}: SKIPPED — {prov.get('skipped')}", file=sys.stderr)
            meta[rid] = {"skipped": prov.get("skipped")}
            continue
        suffix = ".truth-condensed-alt" if args.sensitivity else ".truth-condensed"
        out = FIXTURES / f"{rid}{suffix}.musicxml"
        report = build_condensed(row, alloc, out, force=args.force)
        meta[rid] = {
            "allocation": alloc,
            "allocation_provenance": prov,
            "reference_parts": report["window"]["n_parts"],
            "condensed_parts": report["parts_after_merge"],
            "printed_staves": row["page"].get("n_staves"),
            "condensed_truth": str(out),
            "sha256_16": {"pred": sha(pred), "truth_raw": sha(truth),
                          "truth_condensed": sha(out)},
        }
        raw_pairs.append((rid, pred, truth))
        con_pairs.append((rid, pred, out))

    if not raw_pairs:
        print("nothing to score", file=sys.stderr)
        return 1

    raw = omr_ned_mod.score_batch(raw_pairs, detail=args.detail)
    con = omr_ned_mod.score_batch(con_pairs, detail=args.detail)
    by_raw = {p["name"]: p for p in raw["pairs"]}
    by_con = {p["name"]: p for p in con["pairs"]}

    print()
    print(f"{'row':34s} {'parts':>9s} {'raw NED':>8s} {'raw ed':>7s} "
          f"{'con NED':>8s} {'con ed':>7s} {'explained':>10s}")
    out_rows = []
    for rid, _, _ in raw_pairs:
        r, c = by_raw[rid], by_con[rid]
        share = (r["omr_ed"] - c["omr_ed"]) / r["omr_ed"] if r["omr_ed"] else 0.0
        parts = f"{meta[rid]['reference_parts']}->{meta[rid]['condensed_parts']}"
        print(f"{rid:34s} {parts:>9s} {r['omr_ned']:8.4f} {r['omr_ed']:7d} "
              f"{c['omr_ned']:8.4f} {c['omr_ed']:7d} {100 * share:9.1f}%")
        out_rows.append({
            "row_id": rid, **meta[rid],
            "raw": {k: r[k] for k in ("omr_ned", "omr_ed", "truth_symbols",
                                      "pred_symbols", "categories")},
            "condensed": {k: c[k] for k in ("omr_ned", "omr_ed", "truth_symbols",
                                            "pred_symbols", "categories")},
            "edits_explained": r["omr_ed"] - c["omr_ed"],
            "edit_share_explained": round(share, 4),
        })

    r_ed, c_ed = raw["overall_omr_ed"], con["overall_omr_ed"]
    print()
    print(f"pooled raw       {raw['overall_omr_ned']:.4f}  {r_ed} edits over "
          f"{raw['overall_truth_symbols']} truth + "
          f"{raw['overall_pred_symbols']} pred")
    print(f"pooled condensed {con['overall_omr_ned']:.4f}  {c_ed} edits over "
          f"{con['overall_truth_symbols']} truth + "
          f"{con['overall_pred_symbols']} pred")
    print(f"the convention explains {r_ed - c_ed} of {r_ed} pooled edits "
          f"({100 * (r_ed - c_ed) / r_ed:.1f}%)")
    print("\nRAW is the benchmark headline. The condensed column attributes; it "
          "does not flatter:\nboth the numerator and the symmetric denominator "
          "move when parts are merged.")

    drift = []
    recorded = BENCH / "results.json"
    if recorded.is_file():
        was = {r["row_id"]: (r.get("omr_ned") or {})
               for r in json.loads(recorded.read_text())["rows"]}
        for entry in out_rows:
            old = was.get(entry["row_id"]) or {}
            new = entry["raw"]
            if old and (old.get("omr_ed"), old.get("pred_symbols")) != (
                    new["omr_ed"], new["pred_symbols"]):
                drift.append({"row_id": entry["row_id"],
                              "results_json": {k: old.get(k) for k in
                                               ("omr_ned", "omr_ed",
                                                "pred_symbols")},
                              "measured_here": {k: new[k] for k in
                                                ("omr_ned", "omr_ed",
                                                 "pred_symbols")}})
    if drift:
        print("\n!! RAW DRIFT against results.json — the prediction files were "
              "re-exported\n   since that table was measured. Both columns "
              "above are on THIS tree.", file=sys.stderr)
        for d in drift:
            print(f"   {d['row_id']}: {d['results_json']['omr_ed']} -> "
                  f"{d['measured_here']['omr_ed']} edits", file=sys.stderr)

    payload = {
        "generated_by": "benchmarks/omr-scan-e2e-2026-09/condensation_arm.py",
        "arm": "sensitivity" if args.sensitivity else "condensed",
        "headline_is": "the RAW column in results.json / RESULTS.md",
        "git_head": git_head(),
        "raw_drift_against_results_json": drift or None,
        "pooled": {
            "raw": {"omr_ned": raw["overall_omr_ned"], "omr_ed": r_ed,
                    "truth_symbols": raw["overall_truth_symbols"],
                    "pred_symbols": raw["overall_pred_symbols"],
                    "categories": raw.get("overall_categories")},
            "condensed": {"omr_ned": con["overall_omr_ned"], "omr_ed": c_ed,
                          "truth_symbols": con["overall_truth_symbols"],
                          "pred_symbols": con["overall_pred_symbols"],
                          "categories": con.get("overall_categories")},
            "edits_explained": r_ed - c_ed,
            "edit_share_explained": round((r_ed - c_ed) / r_ed, 4),
        },
        "skipped": {k: v for k, v in meta.items() if "skipped" in v},
        "rows": out_rows,
    }
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
