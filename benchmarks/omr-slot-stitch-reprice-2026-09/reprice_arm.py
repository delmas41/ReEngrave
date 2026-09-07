"""Re-price `OMR_SLOT_STITCH` against the page-normalised truth.

    python3 benchmarks/omr-slot-stitch-reprice-2026-09/reprice_arm.py

Sean's commission (backlog A0b): the flag is OFF because it scores worse, and
the RECORDED REASON is that "musicdiff charges an unpaired truth PART more than
that part's unpaired MEASURES". But unpaired truth parts are the CONDENSATION
artefact — the truth holds 18 parts where the page prints 12 staves — so *any*
structurally faithful output is billed for them. That is a charge for something
other than correctness. The page-normalised truth has no unpaired parts to bill.

FOUR CELLS, ONE musicdiff BATCH: {stitch OFF, stitch ON} x {raw, normalised}.

WHY THE TWO ARMS SHARE ONE TRANSCRIPTION, AND WHY THAT IS NOT THE CACHE TRAP.
`OMR_SLOT_STITCH` is read inside `to_musicxml` — it is an EXPORT decision and
touches no detection. So the arms are produced by exporting ONE stored
transcription twice, which makes the delta exactly the flag and removes the
detector's ~+/-6-edit noise floor from the comparison entirely.

  The documented hazard (`scan_eval.run_pipeline` returning early on an existing
  fixture, so a second arm silently never runs and reports a flawless "identical
  on every row") is about an arm that DID NOT EXECUTE. Here the sharing is by
  construction and is PROVEN to have executed: the two prediction files are
  hashed and must DIFFER on every reached row and be IDENTICAL on every
  unreached one. A cache accident cannot produce that pattern -- it produces
  identical everywhere.

⚠️ THE NORMALISED COLUMN IS A SEPARATE BENCHMARK ERA. OMR-NED is symmetric, so
merging truth parts moves the denominator too. A normalised figure may not be
differenced against ANY un-normalised figure, historical or otherwise. The
comparison this arm makes is ON vs OFF *within* one column, which is legitimate
because both cells share a truth, a tree and a transcription.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "benchmarks" / "omr-scan-e2e-2026-09"))

import page_normalise                                          # noqa: E402
from tools.omr import export as export_mod                     # noqa: E402
from tools.omr import omr_ned as omr_ned_mod                   # noqa: E402

SCAN = ROOT / "benchmarks" / "omr-scan-e2e-2026-09"
FIXTURES = SCAN / "fixtures"
WORKS = SCAN / "works.json"
DERIVED = BENCH / "derived-truth"

OFF_TAG = ".-stitchoff"
ON_TAG = ".-stitchon"


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


def export_with_flag(raw_json: Path, out: Path, on: bool) -> str:
    """Export one stored transcription under one setting of the flag.

    The env var is set and restored around the call, and the result is re-loaded
    from disk each time, so neither arm can inherit state from the other.
    """
    prev = os.environ.get("OMR_SLOT_STITCH")
    os.environ["OMR_SLOT_STITCH"] = "1" if on else "0"
    try:
        result = json.loads(raw_json.read_text())
        xml = export_mod.to_musicxml(result)
    finally:
        if prev is None:
            os.environ.pop("OMR_SLOT_STITCH", None)
        else:
            os.environ["OMR_SLOT_STITCH"] = prev
    out.write_text(xml)
    return xml


def reach(raw_json: Path) -> dict:
    """Can the flag act on this row at all?  Computed from the transcription."""
    result = json.loads(raw_json.read_text())
    systems = [s for pg in result.get("pages", [])
               for s in pg.get("systems", []) if s.get("staves")]
    sizes = sorted({len(s["staves"]) for s in systems})
    ordinal = export_mod._stitch_slots(result)
    by_slot = None
    if ordinal is None:
        by_slot = export_mod._stitch_slots_by_slot(result)
    if ordinal is not None:
        why = "ordinal join SUCCEEDS - flag never consulted"
    elif len(systems) < 2:
        why = "single system - nothing to stitch"
    elif by_slot is None:
        why = "ordinal REFUSED and slot join also abstains (incomplete slots)"
    else:
        why = "ordinal REFUSED, slot join supplies it - FLAG ACTS HERE"
    return {"n_systems": len(systems), "staff_counts": sizes,
            "ordinal_joins": ordinal is not None,
            "slot_join_available": by_slot is not None,
            "reached": ordinal is None and by_slot is not None,
            "why": why}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", nargs="+", default=None)
    ap.add_argument("--out", default=str(BENCH / "results-reprice.json"))
    args = ap.parse_args(argv)

    DERIVED.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    if args.rows:
        rows = [r for r in rows if r["row_id"] in set(args.rows)]

    t0 = time.time()
    pairs: list[tuple] = []
    entries: list[dict] = []
    skipped: list[dict] = []

    for row in rows:
        rid = row["row_id"]
        raw_json = FIXTURES / f"{rid}{OFF_TAG}.omr.json"
        truth = FIXTURES / f"{rid}.truth.musicxml"
        if not raw_json.is_file() or not truth.is_file():
            skipped.append({"row_id": rid, "reason": "no fixture on disk "
                            f"(json={raw_json.is_file()}, truth={truth.is_file()})"})
            continue

        pred_off = FIXTURES / f"{rid}{OFF_TAG}.omr.musicxml"
        pred_on = FIXTURES / f"{rid}{ON_TAG}.omr.musicxml"
        xml_off = export_with_flag(raw_json, pred_off, on=False)
        xml_on = export_with_flag(raw_json, pred_on, on=True)

        e = {
            "row_id": rid, "work_id": row["work_id"],
            "pooled": row.get("pooled", True),
            "reach": reach(raw_json),
            "parts": {"off": xml_off.count("<score-part "),
                      "on": xml_on.count("<score-part ")},
            "sha": {"transcription": sha(raw_json), "truth_raw": sha(truth),
                    "pred_off": sha(pred_off), "pred_on": sha(pred_on)},
        }
        e["predictions_differ"] = e["sha"]["pred_off"] != e["sha"]["pred_on"]

        pairs.append((f"{rid}|off|raw", pred_off, truth))
        pairs.append((f"{rid}|on|raw", pred_on, truth))

        try:
            # REUSE the derived truth scan_eval wrote for the OFF arm where it
            # exists. A derived truth's bytes are NOT reproducible across runs
            # (music21 stamps a fresh <encoding-date> and random instrument
            # ids), so regenerating would silently score the two arms against
            # two different files and make the OFF/normalised cell
            # un-cross-checkable against scan_eval's own reported figure.
            shipped = FIXTURES / f"{rid}.page-normalised.truth.musicxml"
            prov = FIXTURES / f"{rid}.page-normalised.truth.provenance.json"
            if shipped.is_file() and prov.is_file():
                norm = shipped
                rep = json.loads(prov.read_text())
                e["normalised_truth_source"] = "reused from the OFF-arm scan_eval run"
            else:
                norm = DERIVED / f"{rid}.page-normalised.musicxml"
                rep = page_normalise.write(
                    truth, row.get("staves"), norm,
                    source_reference=row["reference"]["catalog_path"])
                e["normalised_truth_source"] = "generated here"
            e["normalised"] = True
            e["transform"] = {
                "version": rep.get("transform_version"),
                "n_source_parts": rep.get("n_source_parts"),
                "n_output_parts": rep.get("n_output_parts"),
                "divisi_share": rep.get("divisi_share"),
                "exact_duplication_share": rep.get("exact_duplication_share"),
            }
            e["sha"]["truth_normalised"] = sha(norm)
            pairs.append((f"{rid}|off|norm", pred_off, norm))
            pairs.append((f"{rid}|on|norm", pred_on, norm))
        except page_normalise.NoHandMap as exc:
            e["normalised"] = False
            e["not_normalised_because"] = str(exc)
        entries.append(e)

    if not pairs:
        print("nothing to score", file=sys.stderr)
        return 1

    t_export = time.time() - t0
    t1 = time.time()
    scored = omr_ned_mod.score_batch(pairs, detail="AllObjects")
    t_score = time.time() - t1
    by_name = {p["name"]: p for p in scored.get("pairs", [])}
    for e in entries:
        rid = e["row_id"]
        for arm in ("off", "on"):
            e[f"{arm}_raw"] = by_name.get(f"{rid}|{arm}|raw")
            if e["normalised"]:
                e[f"{arm}_norm"] = by_name.get(f"{rid}|{arm}|norm")

    def pool(key: str, rows_: list[dict]) -> dict:
        ed = ts = ps = 0
        cats: dict[str, int] = {}
        for e in rows_:
            n = e.get(key)
            if not n:
                return {}
            ed += n["omr_ed"]; ts += n["truth_symbols"]; ps += n["pred_symbols"]
            for k, v in (n.get("categories") or {}).items():
                cats[k] = cats.get(k, 0) + v
        return {"omr_ned": ed / (ts + ps) if (ts + ps) else None, "omr_ed": ed,
                "truth_symbols": ts, "pred_symbols": ps,
                "categories": cats, "n_rows": len(rows_)}

    poolable = [e for e in entries if e.get("pooled", True)]
    norml = [e for e in poolable if e["normalised"]]
    reached = [e for e in poolable if e["reach"]["reached"]]
    unreached = [e for e in poolable if not e["reach"]["reached"]]

    # CONTROL: an unreached row must be identical to the EDIT in both columns.
    control = []
    for e in unreached:
        ok_raw = (e["off_raw"]["omr_ed"] == e["on_raw"]["omr_ed"]
                  and not e["predictions_differ"])
        rec = {"row_id": e["row_id"], "predictions_identical":
               not e["predictions_differ"],
               "raw_edits_identical": e["off_raw"]["omr_ed"] == e["on_raw"]["omr_ed"]}
        if e["normalised"]:
            rec["norm_edits_identical"] = (
                e["off_norm"]["omr_ed"] == e["on_norm"]["omr_ed"])
        rec["PASS"] = ok_raw and rec.get("norm_edits_identical", True)
        control.append(rec)

    doc = {
        "generated_by": "benchmarks/omr-slot-stitch-reprice-2026-09/reprice_arm.py",
        "git_head": git_head(),
        "commission": "backlog A0b - re-price OMR_SLOT_STITCH against the "
                      "page-normalised truth (Sean)",
        "transform_version": page_normalise.TRANSFORM_VERSION,
        "merge_convention": page_normalise.MERGE_CONVENTION,
        "era_warning": "the NORMALISED column is a SEPARATE BENCHMARK ERA and "
                       "may not be differenced against any un-normalised "
                       "figure. ON-vs-OFF WITHIN one column is the valid "
                       "comparison: both cells share a truth, a tree and a "
                       "transcription.",
        "arms_share_one_transcription": (
            "BY CONSTRUCTION - the flag is export-only. Proven executed by the "
            "prediction hashes differing on every reached row."),
        "seconds": {"export_and_normalise": round(t_export, 1),
                    "musicdiff_batch": round(t_score, 1)},
        "reach": {
            "n_reached": len(reached),
            "reached_rows": [e["row_id"] for e in reached],
            "n_unreached": len(unreached),
            "why_unreached": {e["row_id"]: e["reach"]["why"] for e in unreached},
        },
        "control_unreached_rows_must_be_identical": {
            "rows": control,
            "PASS": all(c["PASS"] for c in control) if control else None,
        },
        "pooled_all_rows": {
            "off_raw": pool("off_raw", poolable),
            "on_raw": pool("on_raw", poolable),
        },
        "pooled_normalisable_rows_only": {
            "off_raw": pool("off_raw", norml), "on_raw": pool("on_raw", norml),
            "off_norm": pool("off_norm", norml), "on_norm": pool("on_norm", norml),
        },
        "pooled_reached_rows_only": {
            "off_raw": pool("off_raw", reached), "on_raw": pool("on_raw", reached),
            "off_norm": pool("off_norm", [e for e in reached if e["normalised"]]),
            "on_norm": pool("on_norm", [e for e in reached if e["normalised"]]),
        },
        "skipped": skipped,
        "rows": entries,
    }
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")

    # ---------------------------------------------------------------- report
    print(f"\ngit {doc['git_head']}   transform v{doc['transform_version']}")
    print(f"export+normalise {t_export:.1f}s   musicdiff {t_score:.1f}s "
          f"({len(pairs)} pairs in ONE batch)\n")
    h = (f"{'row':38s} {'reach':>5s} {'prts off/on':>11s} | "
         f"{'RAW off':>8s} {'RAW on':>8s} {'d':>6s} | "
         f"{'NRM off':>8s} {'NRM on':>8s} {'d':>6s}")
    print(h); print("-" * len(h))
    for e in entries:
        r = "YES" if e["reach"]["reached"] else "-"
        orw, onw = e["off_raw"]["omr_ed"], e["on_raw"]["omr_ed"]
        if e["normalised"]:
            onm, onn = e["off_norm"]["omr_ed"], e["on_norm"]["omr_ed"]
            print(f"{e['row_id']:38s} {r:>5s} "
                  f"{e['parts']['off']:>5d}/{e['parts']['on']:<5d} | "
                  f"{orw:>8d} {onw:>8d} {onw-orw:>+6d} | "
                  f"{onm:>8d} {onn:>8d} {onn-onm:>+6d}")
        else:
            print(f"{e['row_id']:38s} {r:>5s} "
                  f"{e['parts']['off']:>5d}/{e['parts']['on']:<5d} | "
                  f"{orw:>8d} {onw:>8d} {onw-orw:>+6d} | "
                  f"{'—':>8s} {'—':>8s} {'—':>6s}")
    print()
    for label, key in (("ALL rows, raw truth", "pooled_all_rows"),
                       ("NORMALISABLE rows", "pooled_normalisable_rows_only"),
                       ("REACHED rows only", "pooled_reached_rows_only")):
        p = doc[key]
        print(f"--- {label} ---")
        for cell in ("off_raw", "on_raw", "off_norm", "on_norm"):
            v = p.get(cell)
            if v:
                es = v["categories"].get("entire staff insert/delete", 0)
                em = v["categories"].get("entire measure insert/delete", 0)
                print(f"  {cell:9s} NED {v['omr_ned']:.4f}  {v['omr_ed']:>6d} ed"
                      f"   entire-staff {es:>6d}  entire-measure {em:>6d}")
        print()
    ctl = doc["control_unreached_rows_must_be_identical"]["PASS"]
    print(f"CONTROL (unreached rows identical to the edit): {ctl}")
    print(f"reached: {doc['reach']['n_reached']} / {len(poolable)} pooled rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
