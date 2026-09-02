"""End-to-end accuracy on REAL orchestral music, with truth that costs nothing.

`end_to_end_eval` measures the pipeline against three hand-authored fixtures:
one staff, two staves, four staves. That was the right first baseline, but it
tops out well below the texture this project actually exists for, and the
handoff notes that `ensemble` exists only because a lone staff is a different
problem from an ensemble one. Nothing measured a conductor's page.

The Gradus score library has ~97 orchestral movements as MusicXML — Beethoven
1-9, Brahms 1-4, Bruckner 5, Dvorak 9, Mahler 5, Mozart 40/41, Tchaikovsky 4/6,
Boléro. Rendering an excerpt of one back to PDF gives a dense orchestral page
whose every note is known exactly, for free, at eighteen staves.

    python3 -m tools.omr.training.orchestral_eval --works beethoven-sym5-mvt1
    python3 -m tools.omr.training.orchestral_eval --measures 1-8 --out after.json

WHAT THIS DOES AND DOES NOT MEASURE. The input is ENGRAVED, not scanned: no
foxing, no bleed-through, no skew, no broken staff lines. So a failure here is
a failure of recognition on dense music, and cannot be blamed on print quality
— which is exactly the confound that makes the orchestral numbers elsewhere in
this repository hard to read. It says nothing about scan robustness. Both
matter; this isolates one.

It also runs the dossier checks on the result, so the same command reports how
many disagreements the external-truth layer catches on a page whose true
content is known.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import fitz
from music21 import converter

from tools.omr.dossier import find_dossier, summarize
from tools.omr.export import to_musicxml
from tools.omr.training.end_to_end_eval import (
    DEFAULT_WEIGHTS,
    align,
    part_sequences,
    structure,
)
from tools.omr.transcribe import transcribe

ROOT = Path(__file__).resolve().parents[3]
BENCH_DIR = ROOT / "benchmarks" / "omr-orchestral-e2e"
SCORE_DIR = Path("/Users/seanjohnson/Desktop/gradus-vercel/public/scores")

# Kept small on purpose: an eighteen-part excerpt of even a few bars fills a
# page, and the point is density per page, not length.
DEFAULT_MEASURES = (1, 8)

# One per texture family rather than all 97, so a default run stays minutes not
# hours. `--works` takes any work_id that has a dossier.
DEFAULT_WORKS = (
    "beethoven-sym5-mvt1",   # classical orchestra, 18 parts, one alto clef
    "brahms-sym1-mvt1",      # romantic, thicker inner voices
    "mahler-sym5-mvt1",      # late romantic, largest forces
)


def excerpt(work_id: str, first: int, last: int,
            out_dir: Path) -> tuple[Path, Path, int]:
    """Write `<work>.musicxml` (the truth) and `<work>.pdf` (the input).

    Returns `(truth_xml, pdf, last_measure_used)` — see the page-fitting note
    inside.
    """
    src = None
    for suffix in (".mxl", ".musicxml"):
        candidate = SCORE_DIR / f"{work_id}{suffix}"
        if candidate.is_file():
            src = candidate
            break
    if src is None:
        raise FileNotFoundError(f"no score for {work_id} under {SCORE_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    parsed = converter.parse(str(src))
    n_parts = len(parsed.parts)

    # THE EXCERPT MUST FIT ON ONE PAGE, and that is not a cosmetic preference.
    # `export.to_musicxml` emits one <part> per (page, system, staff), so a part
    # is NOT continuous across a page break: transcribing three pages of a
    # 21-staff score yields 63 parts, not 21 parts three times as long. Scoring
    # a multi-page render therefore measures the exporter's page handling rather
    # than recognition, and scoring only page 0 against the FULL excerpt's truth
    # silently caps recall at the fraction of the music that landed on it —
    # which is what an 8-measure Brahms excerpt spanning 3 pages was doing.
    #
    # So shrink the range until LilyPond gives back a single page, and take the
    # truth from exactly that range. The number of measures actually used is
    # returned so the report can say what was measured.
    last_used = last
    while last_used >= first:
        score = parsed.measures(first, last_used)
        xml = out_dir / f"{work_id}.musicxml"
        score.write("musicxml", fp=str(xml))

        ly = out_dir / f"{work_id}.ly"
        subprocess.run(["musicxml2ly", "-o", str(ly), str(xml)],
                       check=True, capture_output=True)
        src_ly = ly.read_text()
        src_ly = src_ly.replace("\\header {", "\\header {\n  tagline = ##f")
        # PAPER MUST BE SIZED TO THE SCORE, and getting this wrong invalidates
        # the whole measurement. Rendering a 38-part Mahler page on A4 leaves
        # LilyPond ~1.0 staff-space between staves — the page becomes one
        # continuous ladder of evenly spaced lines with no visible boundary
        # between one staff and the next, which no staff detector can segment
        # and which real engraving never does. Measured on that excerpt:
        #
        #     paper   staves found   ambiguous ladders   inter-staff gap
        #     a4         31 / 38            5              1.0 spaces
        #     a3         38 / 38            0              1.8 spaces
        #     a2         38 / 38            0              4.3 spaces
        #
        # So the "staff phasing" failure that made Mahler look catastrophic was
        # an artifact of this fixture, not of the pipeline. Scale the sheet with
        # the part count instead.
        paper = "a4" if n_parts <= 20 else ("a3" if n_parts <= 40 else "a2")
        # A conductor's score is engraved small; 16pt is where real orchestral
        # prints sit.
        src_ly = (f'#(set-default-paper-size "{paper}")\n'
                  "#(set-global-staff-size 16)\n") + src_ly
        ly.write_text(src_ly)
        subprocess.run(["lilypond", "-s", "-o", work_id, f"{work_id}.ly"],
                       cwd=out_dir, check=True, capture_output=True)
        pdf = out_dir / f"{work_id}.pdf"
        with fitz.open(pdf) as doc:
            n_pages = doc.page_count
        if n_pages == 1 or last_used == first:
            return xml, pdf, last_used
        last_used -= 1
    raise RuntimeError(f"{work_id}: could not fit any excerpt on one page")


def run_work(work_id: str, *, first: int, last: int, work_dir: Path,
             weights: str, dpi: int | None, use_dossier: bool,
             direction_text: bool = False) -> dict[str, Any]:
    truth_xml, pdf, last_used = excerpt(work_id, first, last, work_dir)
    dossier = find_dossier(work_id) if use_dossier else None

    # dpi=None takes `transcribe`'s default rather than restating it here.
    opts = {"dpi": dpi} if dpi is not None else {}
    result = transcribe(pdf_path=pdf, pages=[0], weights=weights,
                        dossier=dossier, progress=False,
                        read_direction_text=direction_text, **opts)
    omr_xml = work_dir / f"{work_id}.omr.musicxml"
    omr_xml.write_text(to_musicxml(result))

    page = result["pages"][0]
    truth_struct = structure(truth_xml)
    omr_struct = structure(omr_xml)
    scores = align(part_sequences(truth_xml), part_sequences(omr_xml))

    return {
        "work_id": work_id,
        "measures": [first, last_used],
        # Kept so `--omr-ned` can score the pair after every work has run: the
        # pooled OMR-NED is only meaningful over the whole set, so it cannot be
        # computed here one work at a time.
        "truth_xml": str(truth_xml),
        "omr_xml": str(omr_xml),
        "truth": truth_struct,
        "omr": omr_struct,
        "detected": {
            "systems": len(page["systems"]),
            "staves": sum(len(s["staves"]) for s in page["systems"]),
        },
        "notes": scores,
        "rhythm_reconciliations": result.get("n_rhythm_reconciliations", 0),
        "dossier_warnings": summarize(result.get("dossier_warnings", [])),
        "dossier_used": dossier is not None,
        "direction_text": result.get("direction_text"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--works", nargs="+", default=list(DEFAULT_WORKS))
    ap.add_argument("--measures", default=f"{DEFAULT_MEASURES[0]}-{DEFAULT_MEASURES[1]}",
                    help="measure range of the excerpt, e.g. 1-8")
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--dpi", type=int, default=None,
                    help="override the pipeline default")
    ap.add_argument("--no-dossier", action="store_true",
                    help="run without the dossier, to measure what it adds")
    ap.add_argument("--direction-text", action="store_true",
                    help="read the words printed inside each system with "
                         "Surya and export them as MusicXML <words> — the "
                         "`wrong direction` category, 151 of the 1715 pooled "
                         "edits at the 0.2449 baseline. Needs .venv-surya.")
    ap.add_argument("--work-dir", type=Path, default=BENCH_DIR / "fixtures")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--omr-ned", action="store_true",
                    help="also score each pair with OMR-NED, the Sheet Music "
                         "Benchmark metric, so the result is comparable to "
                         "published numbers (needs `python3 -m tools.omr.omr_ned "
                         "--bootstrap` once)")
    ap.add_argument("--omr-ned-detail", default="AllObjects",
                    help="musicdiff DetailLevel; NotesAndRests restricts the "
                         "score to pitch and rhythm, which is the closest "
                         "comparison to the note recall reported above")
    args = ap.parse_args(argv)

    first, _, last = args.measures.partition("-")
    first, last = int(first), int(last or first)

    header = (f"{'work':22s} {'bars':>5s} {'parts':>11s} {'measures':>10s} "
              f"{'notes':>12s} {'recall':>7s} {'prec':>6s} {'dur':>6s}  dossier")
    print(header)
    results = []
    # An enrichment that failed like a DEFECT, as opposed to abstaining. Kept
    # so the run can end non-zero: a benchmark that quietly measures a pipeline
    # with a documented pass broken is worse than one that refuses to report.
    broken_passes: list[tuple[str, str, str | None]] = []
    for work_id in args.works:
        try:
            r = run_work(work_id, first=first, last=last, work_dir=args.work_dir,
                         weights=args.weights, dpi=args.dpi,
                         use_dossier=not args.no_dossier,
                         direction_text=args.direction_text)
        except Exception as exc:  # noqa: BLE001 — one bad work must not stop the run
            print(f"{work_id:22s} FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        results.append(r)
        n = r["notes"]
        ctx = r.get("contextual") or {}
        if ctx.get("looks_like_a_bug"):
            broken_passes.append((work_id, "contextual", ctx.get("reason")))
        elif not ctx.get("available", True):
            print(f"{'':22s} note: contextual unavailable — "
                  f"{ctx.get('reason')}", file=sys.stderr)
        flags = r["dossier_warnings"]
        used = r["measures"][1] - r["measures"][0] + 1
        print(f"{work_id:22s} {used:>5d} "
              f"{r['omr']['parts']:>5d}/{r['truth']['parts']:<5d} "
              f"{r['omr']['measures']:>4d}/{r['truth']['measures']:<5d} "
              f"{n['omr_notes']:>5d}/{n['truth_notes']:<6d} "
              f"{n['pitch_recall']:>7.3f} {n['pitch_precision']:>6.3f} "
              f"{n['duration_rate']:>6.3f}  "
              + (", ".join(f"{k.replace('dossier_', '')}={v}"
                           for k, v in sorted(flags.items())) or "clean"))

    if args.omr_ned and results:
        # Imported here so the benchmark still runs with no musicdiff venv.
        from tools.omr import omr_ned as omr_ned_mod

        pairs = [(r["work_id"], r["omr_xml"], r["truth_xml"]) for r in results]
        try:
            scored = omr_ned_mod.score_batch(pairs, detail=args.omr_ned_detail)
        except omr_ned_mod.OmrNedError as exc:
            print(f"\nOMR-NED unavailable: {exc}", file=sys.stderr)
        else:
            by_name = {p["name"]: p for p in scored.get("pairs", [])}
            for r in results:
                r["omr_ned"] = by_name.get(r["work_id"])
            print()
            print(omr_ned_mod.format_report(scored))

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.out}")

    if broken_passes:
        print("\nBROKEN, not abstaining — these are defects and the numbers "
              "above were measured without them:", file=sys.stderr)
        for work_id, pass_name, reason in broken_passes:
            print(f"  {work_id}: {pass_name}: {reason}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
