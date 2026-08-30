"""A wide, ground-truth-free profile of the pipeline over the whole local corpus.

Every wrong conclusion this project has corrected recently came from the same
place: a confident number measured on too little. Clef accuracy rests on 52
hand-read staves across three pages, key signatures on 42 across three. Those
are the right sets for ACCURACY — they are the only ones with truth — but they
cannot tell you where the pipeline crashes, where it silently abstains, or
whether a change that looks neutral on three pages is neutral on four hundred.

This sweep needs no ground truth. It runs the real pipeline over a sample of
every score on this machine and records, per page, what came out: staves,
systems, measures, notes, where each clef came from, which key signatures were
read and why the rest were not, every internal-consistency warning, and any
exception. What it produces is a BASELINE — a file you diff against after a
change, to see the blast radius outside the three pages you were aiming at.

Robust by construction, because it runs unattended:

  * one JSON line per page, flushed immediately, so a run that dies keeps
    everything it had finished;
  * resumable — pages already in the output are skipped, so re-running
    continues rather than restarting;
  * a page that raises is recorded as a row with its traceback and the sweep
    carries on, since crashes are a finding, not an interruption.

    python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --every 6 --max-per-score 40
    python3 benchmarks/omr-corpus-sweep-2026-08/sweep.py --summarize
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "sweep.jsonl"
WEIGHTS = ROOT / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
GRADUS = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")

# (key, path, dpi). DPI follows the corpus convention already established in
# phase1_layout_eval: 600 for keyboard/small-format, 300 for dense orchestral.
SCORES: list[tuple[str, Path, int]] = [
    ("wtc",           GRADUS / "PDF Scores/IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 600),
    ("beet5",         GRADUS / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 600),
    ("kirchhoff",     GRADUS / "Kirchhoff_L'ABC-Musical.pdf", 600),
    ("handel-red",    GRADUS / "PDF Scores/Haendel_Messiah_reduction.pdf", 600),
    ("handel-lead",   GRADUS / "PDF Scores/Haendel_Messiah_lead-sheet.pdf", 600),
    ("lamer",         GRADUS / "PDF Scores/IMSLP15420-Debussy_-_La_Mer_(orch._score).pdf", 300),
    ("mahler5",       GRADUS / "PDF Scores/Mahler_5_.pdf", 300),
    ("bolero",        GRADUS / "PDF Scores/IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 300),
    ("beet5-imslp",   ROOT / "tools/omr/training/data/imslp/beethoven-symphony-5/pdfs/imslp-575951/score.pdf", 450),
    ("pastoral",      ROOT / "tools/omr/training/data/imslp/beethoven-symphony-6/pdfs/imslp-504082/score.pdf", 450),
]


def page_count(pdf: Path) -> int:
    import fitz
    with fitz.open(pdf) as doc:
        return doc.page_count


def profile(result: dict) -> dict:
    """Reduce one transcribe() result to the numbers worth keeping."""
    page = result["pages"][0]
    clef_sources: Counter = Counter()
    clefs: Counter = Counter()
    unread_reasons: Counter = Counter()
    warnings: Counter = Counter()
    n_staves = n_measures = n_notes = n_key_read = 0

    for sysm in page["systems"]:
        for st in sysm["staves"]:
            n_staves += 1
            clef_sources[st.get("clef_source") or "defaulted"] += 1
            clefs[st.get("clef") or "none"] += 1
            if st.get("key_signature_read"):
                n_key_read += 1
            reason = st.get("key_signature_unread_reason")
            if reason:
                # Keep the SHAPE of the reason, not its numbers, so they group.
                unread_reasons[reason.split(":")[0][:60]] += 1
            for key in ("measure_count_warning", "clef_advisory",
                        "key_signature_warning", "time_signature_warning"):
                if st.get(key):
                    warnings[key] += 1
            for m in st.get("measures", []):
                n_measures += 1
                n_notes += sum(1 for d in m.get("detections", [])
                               if d.get("category") == "notehead")
                for key in ("phase1_warning", "rhythm_warning",
                            "rhythm_reconciliation", "column_rhythm_warning"):
                    if m.get(key):
                        warnings[key] += 1

    return {
        "systems": len(page["systems"]),
        "staves": n_staves,
        "measures": n_measures,
        "noteheads": n_notes,
        "key_signatures_read": n_key_read,
        "clef_sources": dict(clef_sources),
        "clefs": dict(clefs),
        "key_unread_reasons": dict(unread_reasons),
        "warnings": dict(warnings),
    }


def done_keys() -> set[tuple[str, int]]:
    if not OUT.exists():
        return set()
    out = set()
    for line in OUT.read_text().splitlines():
        try:
            row = json.loads(line)
            out.add((row["score"], row["page"]))
        except Exception:  # noqa: BLE001 — a torn final line is expected
            continue
    return out


def run(every: int, max_per_score: int, only: list[str] | None) -> None:
    from tools.omr.transcribe import transcribe

    already = done_keys()
    print(f"resuming: {len(already)} page(s) already recorded", flush=True)
    jobs: list[tuple[str, Path, int, int]] = []
    for key, pdf, dpi in SCORES:
        if only and key not in only:
            continue
        if not pdf.exists():
            print(f"  {key}: PDF not on this machine, skipped", flush=True)
            continue
        n = page_count(pdf)
        pages = list(range(0, n, every))[:max_per_score]
        jobs += [(key, pdf, p, dpi) for p in pages if (key, p) not in already]

    print(f"{len(jobs)} page(s) to run", flush=True)
    with OUT.open("a") as fh:
        for i, (key, pdf, p, dpi) in enumerate(jobs, 1):
            t0 = time.perf_counter()
            row: dict = {"score": key, "page": p, "dpi": dpi}
            try:
                res = transcribe(pdf_path=pdf, pages=[p], weights=WEIGHTS, dpi=dpi)
                row.update(profile(res))
                row["ok"] = True
            except Exception as exc:  # noqa: BLE001 — a crash is a finding
                row["ok"] = False
                row["error"] = f"{type(exc).__name__}: {exc}"[:300]
                row["traceback"] = traceback.format_exc()[-1200:]
            row["seconds"] = round(time.perf_counter() - t0, 1)
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            flag = "" if row["ok"] else "  <-- CRASH"
            print(f"[{i}/{len(jobs)}] {key} p{p}: {row['seconds']}s{flag}", flush=True)


def summarize() -> None:
    rows = [json.loads(l) for l in OUT.read_text().splitlines() if l.strip()]
    ok = [r for r in rows if r.get("ok")]
    bad = [r for r in rows if not r.get("ok")]
    print(f"pages: {len(rows)}   ok: {len(ok)}   crashed: {len(bad)}")
    if bad:
        print("\ncrashes:")
        for r in Counter((r["score"], r.get("error", "")[:70]) for r in bad).most_common():
            print(f"   {r[1]:>3}x  {r[0][0]:<12} {r[0][1]}")

    tot = Counter()
    for r in ok:
        for k, v in r.get("clef_sources", {}).items():
            tot[k] += v
    staves = sum(tot.values())
    print(f"\nclef source over {staves} staves on {len(ok)} pages:")
    for k, v in tot.most_common():
        print(f"   {k:<16} {v:>6}  {100*v/max(staves,1):>5.1f}%")

    read = sum(r.get("key_signatures_read", 0) for r in ok)
    print(f"\nkey signatures read: {read}/{staves} staves ({100*read/max(staves,1):.1f}%)")
    reasons = Counter()
    for r in ok:
        for k, v in r.get("key_unread_reasons", {}).items():
            reasons[k] += v
    for k, v in reasons.most_common(8):
        print(f"   {v:>6}  {k}")

    warn = Counter()
    for r in ok:
        for k, v in r.get("warnings", {}).items():
            warn[k] += v
    print("\nwarnings raised:")
    for k, v in warn.most_common():
        print(f"   {v:>6}  {k}")

    print(f"\nnoteheads: {sum(r.get('noteheads', 0) for r in ok)}   "
          f"measures: {sum(r.get('measures', 0) for r in ok)}   "
          f"total runtime: {sum(r.get('seconds', 0) for r in ok)/3600:.2f} h")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=int, default=6, help="sample every Nth page")
    ap.add_argument("--max-per-score", type=int, default=40)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--summarize", action="store_true")
    args = ap.parse_args()
    if args.summarize:
        summarize()
    else:
        run(args.every, args.max_per_score, args.only)


if __name__ == "__main__":
    main()
