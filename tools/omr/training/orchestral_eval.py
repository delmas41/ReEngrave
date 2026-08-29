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
        # A conductor's score is engraved small; 16pt is where real orchestral
        # prints sit and keeps eighteen staves on one page.
        src_ly = "#(set-global-staff-size 16)\n" + src_ly
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
             weights: str, dpi: int | None, use_dossier: bool) -> dict[str, Any]:
    truth_xml, pdf, last_used = excerpt(work_id, first, last, work_dir)
    dossier = find_dossier(work_id) if use_dossier else None

    # dpi=None takes `transcribe`'s default rather than restating it here.
    opts = {"dpi": dpi} if dpi is not None else {}
    result = transcribe(pdf_path=pdf, pages=[0], weights=weights,
                        dossier=dossier, progress=False, **opts)
    omr_xml = work_dir / f"{work_id}.omr.musicxml"
    omr_xml.write_text(to_musicxml(result))

    page = result["pages"][0]
    truth_struct = structure(truth_xml)
    omr_struct = structure(omr_xml)
    scores = align(part_sequences(truth_xml), part_sequences(omr_xml))

    return {
        "work_id": work_id,
        "measures": [first, last_used],
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
    ap.add_argument("--work-dir", type=Path, default=BENCH_DIR / "fixtures")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)

    first, _, last = args.measures.partition("-")
    first, last = int(first), int(last or first)

    header = (f"{'work':22s} {'bars':>5s} {'parts':>11s} {'measures':>10s} "
              f"{'notes':>12s} {'recall':>7s} {'prec':>6s} {'dur':>6s}  dossier")
    print(header)
    results = []
    for work_id in args.works:
        try:
            r = run_work(work_id, first=first, last=last, work_dir=args.work_dir,
                         weights=args.weights, dpi=args.dpi,
                         use_dossier=not args.no_dossier)
        except Exception as exc:  # noqa: BLE001 — one bad work must not stop the run
            print(f"{work_id:22s} FAILED: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
            continue
        results.append(r)
        n = r["notes"]
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

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
