"""Score real SCANNED pages against the reference the work is encoded from.

`orchestral_eval` renders a Gradus MusicXML through LilyPond and scores the
transcription against the file it rendered from. That isolates recognition on
dense music from print quality — deliberately — and it is why the pooled 0.1364
says nothing about what happens when someone hands the pipeline a scan.

This is the other half. Every row is a page of a real IMSLP-style scan, run at
the pipeline's own defaults with NO dossier, scored against the movement's
reference MusicXML trimmed to the measures that page actually holds.

    python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --list
    python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --rows beethoven-sym5-mvt1-984073-p1
    python3 benchmarks/omr-scan-e2e-2026-09/scan_eval.py --score-only   # no transcription

THREE RULES, INHERITED FROM benchmarks/omr-first-run-2026-08 AND NOT RE-DECIDED.

  NO DOSSIER. `data/dossiers/` is generated from the same Gradus MusicXML used
  here as truth, so `--dossier` would hand the run the answer it is being
  scored on. A dossier arm may be reported separately; it is never the headline.

  THE PAGE IS THE TRUTH, NOT THE FILE. Where the printed edition and the
  reference disagree about a clef or a key signature, the page wins — the
  Beethoven print gives Trombe and Timpani no key signature and the Gradus file
  gives them three flats, and a pipeline that reads the page right must not be
  marked wrong for it. That is why `works.json` carries HAND-READ clef and key
  columns rather than taking them from the reference.

  THE MEASURE WINDOW IS INPUT, NEVER DERIVED. It comes from `works.json`, is
  established by a probe that does not use the pipeline, and carries a
  `confidence`. This script REFUSES to print a pooled figure while any scored
  row is `first_pass` — a pooled number over an unverified window is exactly the
  0.8706-against-seventeen-measures mistake with more decimal places.

WHAT IT DOES NOT TOUCH. `benchmarks/omr-ned-2026-08/current-accuracy.json` and
CLAUDE.md's `accuracy:begin name=headline` block are defined as the ENGRAVED
orchestral figure — `orchestral_eval --record` refuses to write them even for a
different work set. The scan figure lives in this directory's own
`results.json` and RESULTS.md.

WHERE THIS LIVES. `orchestral_eval` sits in `tools/omr/training/`; this sits in
its benchmark directory, beside `eval_first_run.py`, because the scan work owns
no pipeline code and every path it writes is under `benchmarks/`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parents[1]
sys.path.insert(0, str(ROOT))

from tools.library.score_library import library_root  # noqa: E402
from tools.omr import omr_ned as omr_ned_mod  # noqa: E402
from tools.omr.export import to_musicxml  # noqa: E402
from tools.omr.transcribe import DEFAULT_WEIGHTS, transcribe  # noqa: E402

WORKS = BENCH / "works.json"
FIXTURES = BENCH / "fixtures"
TRIMMER = BENCH / "trim_reference.py"
VENV_PY = ROOT / ".venv-omrned" / "bin" / "python"

#: Workstream A owns the CPU for its own eval runs. A second ultralytics process
#: does not fail, it just makes both slower and the timings meaningless.
BUSY_PATTERN = "orchestral_eval"


# ---------------------------------------------------------------- compute

def cpu_busy() -> list[str]:
    """PIDs of real eval runs — not shells that merely mention one.

    `pgrep -f orchestral_eval` matches any command line containing the string,
    which on this machine includes the monitoring shell wrappers another
    worktree leaves around and the grep looking for them. Requiring the
    EXECUTABLE to be a Python is what separates a run from a mention.
    """
    out = subprocess.run(["ps", "-Ao", "pid=,comm=,args="],
                         capture_output=True, text=True)
    busy = []
    for line in out.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        pid, comm, argv = parts
        if "python" in comm.lower() and BUSY_PATTERN in argv:
            busy.append(pid)
    return busy


def wait_for_cpu(poll_s: int = 60, limit_s: int = 0) -> bool:
    waited = 0
    while cpu_busy():
        if limit_s and waited >= limit_s:
            return False
        print(f"  … {BUSY_PATTERN} running; waiting {poll_s}s "
              f"(waited {waited}s)", flush=True)
        time.sleep(poll_s)
        waited += poll_s
    return True


# ---------------------------------------------------------------- metadata

def load_rows() -> tuple[dict, list[dict]]:
    doc = json.loads(WORKS.read_text())
    rows = doc["rows"]
    by_id = {r["row_id"]: r for r in rows}
    for row in rows:
        staves = row.get("staves")
        if isinstance(staves, str) and staves.startswith("same-as:"):
            row["staves"] = by_id[staves.split(":", 1)[1]]["staves"]
    return doc, rows


def resolve(row: dict) -> tuple[Path, Path]:
    lib = library_root()
    pdf = lib / row["edition"]["catalog_path"]
    ref = lib / row["reference"]["catalog_path"]
    for label, path in (("edition PDF", pdf), ("reference", ref)):
        if not path.is_file():
            raise FileNotFoundError(f"{row['row_id']}: {label} missing: {path}")
    return pdf, ref


def runnable(row: dict) -> str | None:
    """Why this row cannot be run, or None."""
    win = row["window"]
    if win.get("first_ref_measure") is None or win.get("last_ref_measure") is None:
        return "window not established (first/last_ref_measure is null)"
    return None


# ---------------------------------------------------------------- stages

def trim_truth(row: dict, ref: Path, *, force: bool = False) -> tuple[Path, dict]:
    win = row["window"]
    first, last = win["first_ref_measure"], win["last_ref_measure"]
    out = FIXTURES / f"{row['row_id']}.truth.musicxml"
    report_path = FIXTURES / f"{row['row_id']}.truth.json"
    if out.is_file() and report_path.is_file() and not force:
        return out, json.loads(report_path.read_text())
    if not VENV_PY.is_file():
        raise SystemExit(
            f"no musicdiff venv at {VENV_PY} — "
            "python3 -m tools.omr.omr_ned --bootstrap")
    proc = subprocess.run(
        [str(VENV_PY), str(TRIMMER), "--source", str(ref),
         "--first", str(first), "--last", str(last), "--out", str(out)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"{row['row_id']}: trim failed\n{proc.stderr[-2000:]}")
    report = json.loads(proc.stdout)
    report_path.write_text(json.dumps(report, indent=1) + "\n")
    return out, report


def run_pipeline(row: dict, pdf: Path, protocol: dict, *,
                 force: bool = False, tag: str = "") -> tuple[Path, Path]:
    pred = FIXTURES / f"{row['row_id']}{tag}.omr.musicxml"
    raw = FIXTURES / f"{row['row_id']}{tag}.omr.json"
    if pred.is_file() and raw.is_file() and not force:
        return pred, raw

    page = row["page"]["pdf_page_index"]
    t0 = time.time()
    result = transcribe(
        pdf_path=pdf,
        pages=[page],
        # OMR_SCAN_EVAL_WEIGHTS lets an A/B arm score a candidate scan checkpoint
        # against the shipped scan weights; unset = DEFAULT_WEIGHTS (the shipped
        # scan slot). Pair with --tag so the arms land in separate fixtures.
        weights=str(os.getenv("OMR_SCAN_EVAL_WEIGHTS", "").strip() or DEFAULT_WEIGHTS),
        dpi=protocol["dpi"],
        conf_threshold=protocol["conf_threshold"],
        imgsz=protocol["imgsz"],
        dossier=None,                       # see the module docstring
        read_direction_text=protocol["read_direction_text"],
        progress=False,
    )
    elapsed = time.time() - t0
    result["_scan_eval_seconds"] = round(elapsed, 1)
    FIXTURES.mkdir(parents=True, exist_ok=True)
    pred.write_text(to_musicxml(result))
    raw.write_text(json.dumps(result, default=str) + "\n")
    return pred, raw


# ---------------------------------------------------------------- note recall

def _pitches(part) -> tuple[Counter, Counter, Counter]:
    """Every sounding pitch in a part; chords expanded to one entry per pitch."""
    exact: Counter = Counter()
    step: Counter = Counter()
    dur: Counter = Counter()
    for note in part.recurse().notes:
        ql = round(float(note.duration.quarterLength), 4)
        for pitch in note.pitches:
            exact[pitch.nameWithOctave] += 1
            step[f"{pitch.step}{pitch.octave}"] += 1
            dur[(pitch.nameWithOctave, ql)] += 1
    return exact, step, dur


def _score(truth: Counter, got: Counter) -> dict:
    matched = sum((truth & got).values())
    n_t, n_g = sum(truth.values()), sum(got.values())
    return {"truth": n_t, "omr": n_g, "matched": matched,
            "recall": round(matched / n_t, 4) if n_t else None,
            "precision": round(matched / n_g, 4) if n_g else None}


def note_recall(row: dict, truth_xml: Path, pred_xml: Path) -> dict | None:
    """Multiset pitch recall per PRINTED staff.

    Multisets, not sequences: a printed staff can carry two reference parts
    (Flauti is Flute 1 + Flute 2) and the reading order of two condensed parts
    on one staff is genuinely ambiguous, so an order-sensitive alignment would
    measure the ambiguity rather than the recognition. Carried over from
    `benchmarks/omr-first-run-2026-08/eval_first_run.py`.
    """
    staves = row.get("staves")
    if not staves:
        return None
    from music21 import converter

    truth = converter.parse(str(truth_xml))
    pred = converter.parse(str(pred_xml))
    t_parts, p_parts = list(truth.parts), list(pred.parts)

    totals = {k: Counter() for k in ("te", "pe", "ts", "ps", "td", "pd")}
    per_staff = []
    for i, spec in enumerate(staves):
        te, ts, td = Counter(), Counter(), Counter()
        for pi in spec["parts"]:
            if pi < len(t_parts):
                e, s, d = _pitches(t_parts[pi])
                te += e
                ts += s
                td += d
        if i < len(p_parts):
            pe, ps, pd = _pitches(p_parts[i])
        else:
            pe, ps, pd = Counter(), Counter(), Counter()
        per_staff.append({"staff": spec["name"], "exact": _score(te, pe),
                          "step": _score(ts, ps), "with_duration": _score(td, pd)})
        for key, c in (("te", te), ("pe", pe), ("ts", ts), ("ps", ps),
                       ("td", td), ("pd", pd)):
            totals[key] += c

    return {
        "positional": len(p_parts) == len(staves),
        "n_pred_parts": len(p_parts),
        "n_printed_staves": len(staves),
        "pooled": {"exact": _score(totals["te"], totals["pe"]),
                   "step": _score(totals["ts"], totals["ps"]),
                   "with_duration": _score(totals["td"], totals["pd"])},
        "per_staff": per_staff,
    }


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", nargs="+", default=None,
                    help="row_ids to run (default: every runnable row)")
    ap.add_argument("--list", action="store_true",
                    help="show the rows and their window confidence, then exit")
    ap.add_argument("--score-only", action="store_true",
                    help="do not transcribe; score whatever is already in "
                         "fixtures/ (safe while another job owns the CPU)")
    ap.add_argument("--force", action="store_true",
                    help="re-transcribe and re-trim even if fixtures exist")
    ap.add_argument("--wait-for-cpu", action="store_true",
                    help=f"poll until no {BUSY_PATTERN} process is running "
                         "before each transcription")
    ap.add_argument("--dpi", type=int, default=None,
                    help="override the protocol's render dpi. NOT part of the "
                         "headline protocol — it exists because `--dpi` is not "
                         "a resolution control across editions: the raster size "
                         "is dpi times the PDF's DECLARED PAGE BOX, and two "
                         "scans of one plate can declare boxes differing 2x. "
                         "Use with --tag so the arm lands in its own fixtures.")
    ap.add_argument("--direction-text", action=argparse.BooleanOptionalAction,
                    default=None,
                    help="force the direction-text reader on or off, overriding "
                         "the protocol. The protocol pins `read_direction_text` "
                         "to null — pass None to transcribe, i.e. the pipeline "
                         "default (ON since 2026-09-02) — so a default scan run "
                         "reads directions; `--no-direction-text` measures the "
                         "OFF arm on the same tree. Use with --tag so the arms "
                         "land in separate fixtures.")
    ap.add_argument("--tag", default="",
                    help="suffix for fixture and row names, for side arms")
    ap.add_argument("--out", type=Path, default=BENCH / "results.json")
    ap.add_argument("--detail", default="AllObjects",
                    help="musicdiff DetailLevel; NotesAndRests scores pitch and "
                         "rhythm only")
    args = ap.parse_args(argv)

    doc, rows = load_rows()
    protocol = dict(doc["protocol"])
    if args.dpi is not None:
        protocol["dpi"] = args.dpi
    # null in the protocol means "use the pipeline default"; the flag forces
    # either arm so the two can be compared on one tree.
    if args.direction_text is not None:
        protocol["read_direction_text"] = args.direction_text
    tag = f".{args.tag}" if args.tag else ""
    wanted = args.rows or [r["row_id"] for r in rows]
    selected = [r for r in rows if r["row_id"] in wanted]
    missing = sorted(set(wanted) - {r["row_id"] for r in selected})
    if missing:
        ap.error(f"unknown row_id(s): {missing}")

    if args.list:
        print(f"{'row_id':38s} {'page':>5s} {'window':>10s} {'conf':>10s}  status")
        for r in rows:
            w = r["window"]
            win = (f"{w['first_ref_measure']}-{w['last_ref_measure']}"
                   if w.get("last_ref_measure") is not None else "—")
            why = runnable(r)
            print(f"{r['row_id']:38s} {r['page']['pdf_page_index']:>5d} "
                  f"{win:>10s} {w['confidence']:>10s}  "
                  f"{'BLOCKED: ' + why if why else 'ok'}")
        return 0

    FIXTURES.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    pairs: list[tuple[str, Path, Path]] = []

    for row in selected:
        rid = row["row_id"]
        why = runnable(row)
        if why:
            print(f"{rid}: SKIPPED — {why}", file=sys.stderr)
            continue
        pdf, ref = resolve(row)
        truth_xml, trim_report = trim_truth(row, ref, force=args.force)

        pred_xml = FIXTURES / f"{rid}{tag}.omr.musicxml"
        if not pred_xml.is_file() or args.force:
            if args.score_only:
                print(f"{rid}: no prediction in fixtures/ and --score-only; "
                      f"skipped", file=sys.stderr)
                continue
            if args.wait_for_cpu:
                wait_for_cpu()
            elif cpu_busy():
                print(f"{rid}: REFUSED — {BUSY_PATTERN} is running. Use "
                      f"--wait-for-cpu, or come back later.", file=sys.stderr)
                continue
            print(f"{rid}: transcribing page {row['page']['pdf_page_index']} "
                  f"of {pdf.name} …", flush=True)
        pred_xml, raw = run_pipeline(row, pdf, protocol, force=args.force, tag=tag)

        result = json.loads(raw.read_text())
        page = result["pages"][0]
        entry = {
            "row_id": rid + tag,
            "label": row.get("label"),
            "dpi": protocol["dpi"],
            "work_id": row["work_id"],
            "imslp_id": row["edition"].get("imslp_id"),
            "pdf_page_index": row["page"]["pdf_page_index"],
            "window": [row["window"]["first_ref_measure"],
                       row["window"]["last_ref_measure"]],
            "leading_pickup": row["window"].get("leading_pickup"),
            "confidence": row["window"]["confidence"],
            "seconds": result.get("_scan_eval_seconds"),
            "truth": {
                "parts": trim_report["window"]["n_parts"],
                "measures": trim_report["window"]["n_measures"],
                "measure_numbers": trim_report["window"]["measure_numbers"],
                "repeats_stripped": trim_report["unmatched_repeats_stripped"],
            },
            "printed": {"systems": row["page"].get("n_systems"),
                        "staves": row["page"].get("n_staves")},
            "detected": {
                "systems": len(page["systems"]),
                "staves": sum(len(s["staves"]) for s in page["systems"]),
                "measures": max((st["n_measures"]
                                 for sy in page["systems"] for st in sy["staves"]),
                                default=0),
            },
            "truth_xml": str(truth_xml),
            "pred_xml": str(pred_xml),
        }
        ctx = result.get("contextual") or {}
        if ctx.get("looks_like_a_bug"):
            entry["broken_pass"] = {"pass": "contextual",
                                    "reason": ctx.get("reason")}
        try:
            entry["notes"] = note_recall(row, truth_xml, pred_xml)
        except Exception as exc:  # noqa: BLE001
            entry["notes_error"] = f"{type(exc).__name__}: {exc}"
        results.append(entry)
        pairs.append((rid + tag, pred_xml, truth_xml))

    if not results:
        print("nothing scored", file=sys.stderr)
        return 1

    try:
        scored = omr_ned_mod.score_batch(pairs, detail=args.detail)
    except omr_ned_mod.OmrNedError as exc:
        print(f"OMR-NED unavailable: {exc}", file=sys.stderr)
        scored = {"pairs": []}
    by_name = {p["name"]: p for p in scored.get("pairs", [])}
    for r in results:
        r["omr_ned"] = by_name.get(r["row_id"])

    # ---- report
    print()
    print(f"{'row':38s} {'win':>7s} {'staves':>9s} {'meas':>7s} "
          f"{'OMR-NED':>8s} {'edits':>7s} {'truth':>6s} {'pred':>6s}  conf")
    for r in results:
        n = r.get("omr_ned") or {}
        pr, de = r["printed"], r["detected"]
        print(f"{r['row_id']:38s} "
              f"{r['window'][0]}-{r['window'][1]:<5} "
              f"{de['staves']:>4d}/{str(pr['staves'] or '?'):<4} "
              f"{de['measures']:>3d}/{r['truth']['measures']:<3d} "
              f"{n.get('omr_ned', float('nan')):>8.4f} "
              f"{n.get('omr_ed', 0):>7d} {n.get('truth_symbols', 0):>6d} "
              f"{n.get('pred_symbols', 0):>6d}  {r['confidence']}")

    unverified = [r["row_id"] for r in results if r["confidence"] != "verified"]
    print()
    if unverified:
        print("POOLED FIGURE WITHHELD — these rows' measure windows are not "
              "verified:")
        for rid in unverified:
            print(f"    {rid}")
        print("  A pooled score over an unverified window is the "
              "0.8706-against-17-measures\n  mistake with more decimal places. "
              "Verify the windows, then re-run.")
    elif scored.get("overall_omr_ned") is not None:
        print(f"POOLED OMR-NED over {len(results)} scanned pages: "
              f"{scored['overall_omr_ned']:.4f}")
        print(f"  {scored.get('overall_omr_ed')} edits over "
              f"{scored.get('overall_truth_symbols')} truth + "
              f"{scored.get('overall_pred_symbols')} predicted symbols")
        cats = scored.get("overall_categories") or {}
        total = sum(cats.values()) or 1
        for cat, count in sorted(cats.items(), key=lambda kv: -kv[1])[:6]:
            print(f"    {cat:38s} {count:>6d}  {100.0 * count / total:5.1f}%")

    payload = {
        "protocol": protocol,
        "generated_by": "benchmarks/omr-scan-e2e-2026-09/scan_eval.py",
        "pooled_withheld_because": unverified or None,
        "pooled": None if unverified else {
            "omr_ned": scored.get("overall_omr_ned"),
            "omr_ed": scored.get("overall_omr_ed"),
            "truth_symbols": scored.get("overall_truth_symbols"),
            "pred_symbols": scored.get("overall_pred_symbols"),
            "categories": scored.get("overall_categories"),
        },
        "rows": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"\nwrote {args.out}")

    broken = [r for r in results if r.get("broken_pass")]
    if broken:
        for r in broken:
            print(f"\n!! {r['row_id']}: {r['broken_pass']['pass']} failed like a "
                  f"DEFECT: {r['broken_pass']['reason']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
