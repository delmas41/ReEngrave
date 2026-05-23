"""Phase 4 extension benchmark — re-runs the 5 real-world PDFs from
benchmarks/omr-real-world with three new features wired in:

  * Octave-clef pitch support (clef8/clef15 → treble_8va/8vb/15ma/15mb)
  * MusicXML voice splitting via <backup>
  * Tie detection (within-cell pairing)

For each PDF: transcribe → JSON, export to .ly and .musicxml, attempt to
compile the .ly with `lilypond`. Captures stats and writes them to
results.json alongside the per-PDF outputs.

Usage (inside the reengrave-backend container):

    python3 /tmp/run_benchmark.py /tmp/bench_pdfs /tmp/bench_out
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

# PDF → page index (0-based) to transcribe.
# Same pages the Phase 4 retrospective benchmark used.
BENCHMARK_PDFS: dict[str, tuple[str, int]] = {
    "bach-wtc":         ("IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 4),
    "handel-leadsheet": ("Haendel_Messiah_lead-sheet.pdf",                          9),
    "handel-reduction": ("Haendel_Messiah_reduction.pdf",                          19),
    "ravel-bolero":     ("IMSLP421137-PMLP03667-Ravel_Bolero.pdf",                  9),
    "beethoven-5":      ("IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 14),
}


WEIGHTS = "/app/tools/omr/training/data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


def count_feature_usage(result: dict) -> dict:
    """Walk the JSON and count uses of the three new features."""
    n_ties = 0
    n_octave_clef_staves = 0
    n_two_voice_measures_lily = 0  # approximated below
    n_clef_8 = 0
    n_clef_15 = 0
    octave_clef_examples = []
    tied_pitch_examples = []
    for page in result.get("pages", []):
        for sys_ in page.get("systems", []):
            for staff in sys_.get("staves", []):
                clef = staff.get("clef") or ""
                if any(suffix in clef for suffix in ("_8va", "_8vb", "_15ma", "_15mb")):
                    n_octave_clef_staves += 1
                    if len(octave_clef_examples) < 3:
                        octave_clef_examples.append(clef)
                    if "_8" in clef:
                        n_clef_8 += 1
                    if "_15" in clef:
                        n_clef_15 += 1
                for measure in staff.get("measures", []):
                    for det in measure.get("detections", []):
                        if det.get("tied_to_next"):
                            n_ties += 1
                            if len(tied_pitch_examples) < 3:
                                tied_pitch_examples.append(det.get("pitch"))
    return {
        "ties_found": n_ties,
        "octave_clef_staves": n_octave_clef_staves,
        "clef_8_uses": n_clef_8,
        "clef_15_uses": n_clef_15,
        "octave_clef_examples": octave_clef_examples,
        "tied_pitch_examples": tied_pitch_examples,
    }


def count_voice_split(musicxml: str) -> int:
    """Number of measures with a <backup> element (= 2-voice measures)."""
    return musicxml.count("<backup>")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: run_benchmark.py <pdf_dir> <out_dir>", file=sys.stderr)
        return 2
    pdf_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, "/app")
    from tools.omr.transcribe import transcribe
    from tools.omr.export import to_lilypond, to_musicxml

    summary = {
        "weights": WEIGHTS,
        "pdfs": {},
    }
    for label, (pdf_name, page) in BENCHMARK_PDFS.items():
        pdf = pdf_dir / pdf_name
        if not pdf.exists():
            print(f"[SKIP] {label}: {pdf} not found")
            summary["pdfs"][label] = {"error": f"PDF not found: {pdf}"}
            continue

        t0 = time.perf_counter()
        print(f"\n[{label}] transcribing {pdf.name} page {page}...", flush=True)
        try:
            result = transcribe(
                pdf_path=pdf,
                pages=[page],
                weights=WEIGHTS,
                conf_threshold=0.25,
                imgsz=1280,
                dpi=300,
                progress=False,
            )
        except Exception as exc:
            print(f"[{label}] transcribe ERROR: {exc}")
            summary["pdfs"][label] = {"error": str(exc)}
            continue
        elapsed = time.perf_counter() - t0

        # Write outputs
        (out_dir / f"{label}.json").write_text(json.dumps(result, indent=2))
        ly = to_lilypond(result)
        (out_dir / f"{label}.ly").write_text(ly)
        mxl = to_musicxml(result)
        (out_dir / f"{label}.musicxml").write_text(mxl)

        # Compile to PDF — let LilyPond bar-check warnings pass; we just
        # care whether it produced a PDF.
        ly_path = out_dir / f"{label}.ly"
        proc = subprocess.run(
            ["lilypond", "--output", str(out_dir / label), str(ly_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(out_dir),
            timeout=180,
        )
        log = proc.stdout.decode("utf-8", errors="replace")
        (out_dir / f"{label}.lilypond.log").write_text(log)
        pdf_out = out_dir / f"{label}.pdf"
        pdf_size = pdf_out.stat().st_size if pdf_out.exists() else 0
        bar_check_warnings = log.count("barcheck failed")

        # Feature usage
        feats = count_feature_usage(result)
        feats["voice_split_measures_mxl"] = count_voice_split(mxl)

        summary["pdfs"][label] = {
            "page": page,
            "n_systems": result["n_systems_total"],
            "n_staves": result["n_staves_total"],
            "n_measures": result["n_measures_total"],
            "n_noteheads": result["n_noteheads_total"],
            "n_pitched": result["n_noteheads_pitched_total"],
            "n_with_duration": result["n_noteheads_with_duration_total"],
            "runtime_s": round(elapsed, 1),
            "pdf_built": pdf_size > 0,
            "pdf_size_bytes": pdf_size,
            "bar_check_warnings": bar_check_warnings,
            "features": feats,
        }
        f = summary["pdfs"][label]
        print(
            f"[{label}] {f['n_measures']} measures, {f['n_noteheads']} noteheads, "
            f"{f['features']['ties_found']} ties, "
            f"{f['features']['octave_clef_staves']} octave-clef staves, "
            f"{f['features']['voice_split_measures_mxl']} two-voice mxl measures, "
            f"PDF {f['pdf_size_bytes']} bytes  ({elapsed:.0f}s)",
            flush=True,
        )

    (out_dir / "results.json").write_text(json.dumps(summary, indent=2))
    print(f"\n=== wrote {out_dir / 'results.json'} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
