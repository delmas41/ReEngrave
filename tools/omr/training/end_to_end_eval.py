"""End-to-end accuracy: does the pipeline recover the notes it was given?

Nothing in this repo has measured that. Every quality figure is either
symbol-level on hand-labeled cells (the F1 98.8%), or COVERAGE rather than
accuracy — `benchmarks/omr-real-world` reports "100% pitch coverage", which
means every detected notehead was assigned a pitch, not that the pitch is
right. A page can score 100% there while reading the wrong notes.

This closes the loop: author a score (so the truth is exact and free), render it
to PDF, run the pipeline, and align what comes back against what went in.

    python3 -m tools.omr.training.end_to_end_eval
    python3 -m tools.omr.training.end_to_end_eval --out after.json --compare before.json

Reported per fixture, in two groups that fail for different reasons:

  STRUCTURE  staves, systems, measures — Phase 1. A structural error moves
             every note after it, so it is reported separately rather than
             folded into the note score.
  NOTES      recall, precision and pitch/duration accuracy over an alignment of
             the two note sequences.

The alignment is a plain longest-common-subsequence over pitch names, which is
deliberately generous: it does not care where a note sits in the bar, only that
the sequence of pitches is right. A stricter measure-aware alignment would score
lower, and the point of a first baseline is to be honest about what it does and
does not check rather than to flatter the pipeline.
"""

from __future__ import annotations

import argparse
import difflib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from music21 import converter

from tools.omr.training.e2e_fixtures import FIXTURES, render
from tools.omr.transcribe import transcribe
from tools.omr.export import to_musicxml


DEFAULT_WEIGHTS = Path(
    "/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
    "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"
)
BENCH_DIR = Path("benchmarks/omr-end-to-end")


def part_sequences(path: Path) -> list[list[tuple[str, float]]]:
    """Per part, every sounding pitch in reading order, as (name, quarterLength).

    Per PART rather than per score, because `flatten()` on a multi-part score
    interleaves the parts by offset: a four-part truth and a one-part OMR
    reading then arrive in genuinely different orders, and any alignment between
    them measures the interleaving rather than the recognition.

    Chords are expanded to one entry per pitch. Counting chord OBJECTS instead
    is an easy mistake and hides a lot: one exported "chord" of 46 pitches reads
    as a single note.
    """
    score = converter.parse(str(path))
    parts = list(score.parts) or [score]
    out: list[list[tuple[str, float]]] = []
    for part in parts:
        seq: list[tuple[str, float]] = []
        for element in part.flatten().notes:
            ql = float(element.duration.quarterLength)
            for pitch in element.pitches:
                seq.append((pitch.nameWithOctave, ql))
        out.append(seq)
    return out


def note_sequence(path: Path) -> list[tuple[str, float]]:
    """All parts concatenated in part order."""
    return [n for seq in part_sequences(path) for n in seq]


def structure(path: Path) -> dict[str, int]:
    score = converter.parse(str(path))
    parts = list(score.parts)
    per_part = [len(list(p.getElementsByClass("Measure"))) for p in parts]
    return {
        "parts": len(parts),
        # The musical bar count, not the sum over parts: summing is not
        # comparable when the two scores disagree about how many parts there are.
        "measures": max(per_part) if per_part else 0,
        "measures_per_part": per_part,
        "notes": len(note_sequence(path)),
    }


def _lcs(truth: list[tuple[str, float]], got: list[tuple[str, float]]) -> tuple[int, int]:
    matcher = difflib.SequenceMatcher(a=[p for p, _ in truth],
                                      b=[p for p, _ in got], autojunk=False)
    matched = duration_ok = 0
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            matched += 1
            if abs(truth[block.a + k][1] - got[block.b + k][1]) < 1e-6:
                duration_ok += 1
    return matched, duration_ok


def align(truth_parts: list[list[tuple[str, float]]],
          got_parts: list[list[tuple[str, float]]]) -> dict[str, Any]:
    """Match part against part where the two agree on how many parts there are,
    and fall back to one concatenated alignment where they do not."""
    paired = len(truth_parts) == len(got_parts)
    if paired:
        matched = duration_ok = 0
        for t, g in zip(truth_parts, got_parts):
            m, d = _lcs(t, g)
            matched += m
            duration_ok += d
    else:
        matched, duration_ok = _lcs([n for s in truth_parts for n in s],
                                    [n for s in got_parts for n in s])
    truth = [n for s in truth_parts for n in s]
    got = [n for s in got_parts for n in s]
    return {
        "part_aligned": paired,
        "truth_notes": len(truth),
        "omr_notes": len(got),
        "pitch_matched": matched,
        "pitch_recall": round(matched / len(truth), 3) if truth else 0.0,
        "pitch_precision": round(matched / len(got), 3) if got else 0.0,
        "duration_ok_on_matched": duration_ok,
        "duration_rate": round(duration_ok / matched, 3) if matched else 0.0,
    }


def run_fixture(name: str, work: Path, weights: Path, dpi: int | None = None,
                imgsz: int | None = None) -> dict[str, Any]:
    truth_xml, pdf = render(name, work)
    # Anything left as None takes `transcribe`'s own default. Restating those
    # defaults here is how the benchmark and the pipeline came to run different
    # configurations twice — see benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md.
    opts = {k: v for k, v in (("dpi", dpi), ("imgsz", imgsz)) if v is not None}
    result = transcribe(pdf_path=pdf, pages=[0], weights=weights, **opts)
    omr_xml = work / f"{name}.omr.musicxml"
    omr_xml.write_text(to_musicxml(result))

    page = result["pages"][0]
    detected = {
        "staves": sum(len(s["staves"]) for s in page["systems"]),
        "systems": len(page["systems"]),
    }
    truth_struct = structure(truth_xml)
    omr_struct = structure(omr_xml)
    scores = align(part_sequences(truth_xml), part_sequences(omr_xml))
    return {
        "truth": truth_struct,
        "omr": omr_struct,
        "detected": detected,
        "notes": scores,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    # The pipeline's own default. The first baseline was taken at 300 and that
    # was simply a mistake: DPI moves these numbers a long way and not in one
    # direction (melody's duration rate 0.29 -> 0.89, keyboard's precision
    # 0.14 -> 0.33 but its recall 0.59 -> 0.41), so a benchmark run at a
    # non-default setting measures a configuration nobody uses.
    # Both left as None so the harness tracks the pipeline's own defaults
    # rather than silently pinning an old value — restating them is how the
    # benchmark and the pipeline came to run different configurations
    # (benchmarks/omr-dpi-imgsz-2026-08/RESULTS.md). Detection is highly
    # sensitive to imgsz, which is now derived per cell:
    # benchmarks/omr-detector-scale/RESULTS.md.
    ap.add_argument("--dpi", type=int, default=None,
                    help="override the pipeline default")
    ap.add_argument("--imgsz", type=int, default=None,
                    help="override the pipeline default; coupled to --dpi")
    ap.add_argument("--keep-dir", type=Path)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--compare", type=Path)
    args = ap.parse_args()

    if not args.weights.exists():
        raise SystemExit(f"weights not found: {args.weights}")
    if shutil.which("lilypond") is None or shutil.which("musicxml2ly") is None:
        raise SystemExit("lilypond and musicxml2ly are needed to render the fixtures")

    work = args.keep_dir or Path(tempfile.mkdtemp(prefix="e2e-"))
    work.mkdir(parents=True, exist_ok=True)

    results: dict[str, Any] = {}
    print(f"{'fixture':10s} {'parts':>12} {'measures':>12} {'notes':>14} "
          f"{'pitch recall':>13} {'precision':>10} {'dur':>6}")
    for name in FIXTURES:
        if args.only and name not in args.only:
            continue
        r = run_fixture(name, work, args.weights, args.dpi, args.imgsz)
        results[name] = r
        t, o, n = r["truth"], r["omr"], r["notes"]
        print(f"{name:10s} {str(o['parts'])+'/'+str(t['parts']):>12} "
              f"{str(o['measures'])+'/'+str(t['measures']):>12} "
              f"{str(n['omr_notes'])+'/'+str(n['truth_notes']):>14} "
              f"{n['pitch_recall']:>13} {n['pitch_precision']:>10} {n['duration_rate']:>6}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2) + "\n")
        print(f"\nwrote {args.out}")
    if args.compare and args.compare.exists():
        prior = json.loads(args.compare.read_text())
        print(f"\n=== change vs {args.compare} ===")
        moved = False
        for name, r in results.items():
            p = prior.get(name)
            if not p:
                continue
            for field in ("pitch_recall", "pitch_precision", "duration_rate", "omr_notes"):
                if p["notes"][field] != r["notes"][field]:
                    moved = True
                    print(f"  {name:10s} {field}: {p['notes'][field]} -> {r['notes'][field]}")
        if not moved:
            print("  (no change)")
    if not args.keep_dir:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
