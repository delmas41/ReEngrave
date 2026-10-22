#!/usr/bin/env python3
"""Clef correction from instrument range: does it fire, and is it right?

Runs the full chain on real pages and reports every proposal. Correctness is
judged by convention — a bassoon staff should read bass or tenor, a viola alto,
a contrabass bass — which is exactly the knowledge the proposal is built on, so
the honest check is the range fit BEFORE and AFTER plus the false-positive count
on staves whose clef is already right.

Usage: python3 benchmarks/omr-system-grouping-2026-08/eval_clefs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.assist import Assist
from tools.omr.contextual import apply_contextual_analysis
from tools.omr.transcribe import transcribe

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")
C = "/Users/seanjohnson/Desktop/ReEngrave/tools/omr/training/data/imslp"
CASES = [
    (f"{C}/beethoven-symphony-4/pdfs/imslp-09340/score.pdf", [59]),
    (f"{C}/beethoven-symphony-1/pdfs/imslp-13842/score.pdf", [59]),
    (f"{C}/beethoven-symphony-3/pdfs/imslp-504077/score.pdf", [59]),
    (f"{C}/beethoven-symphony-2/pdfs/imslp-503997/score.pdf", [59]),
]

# Clefs each instrument conventionally reads. A proposal outside this set is
# wrong regardless of how well the range fits.
CONVENTIONAL = {
    "Flute": {"treble"}, "Oboe": {"treble"}, "Clarinet": {"treble"},
    "Bassoon": {"bass", "tenor"}, "Contrabassoon": {"bass"},
    "Horn": {"treble", "bass"}, "Trumpet": {"treble"},
    "Trombone": {"bass", "tenor", "alto"}, "Tuba": {"bass"},
    "Timpani": {"bass"}, "English horn": {"treble"},
    "Violin": {"treble"}, "Viola": {"alto", "treble"},
    "Cello": {"bass", "tenor", "treble"}, "Contrabass": {"bass"},
    "Harp": {"treble", "bass"}, "Piano": {"treble", "bass"},
}


def main() -> int:
    total = ok = odd = applied = restated = 0
    for pdf, pages in CASES:
        result = transcribe(pdf_path=Path(pdf), pages=pages, weights=WEIGHTS,
                            dpi=300, imgsz=2048, progress=False)
        summary = apply_contextual_analysis(result, pdf_path=pdf, dpi=300, assist=Assist('none'))
        name = Path(pdf).parents[1].name
        if not summary["available"]:
            print(f"\n=== {name} p{pages[0]} — skipped: {summary['reason']}")
            continue
        print(f"\n=== {name} p{pages[0]} — {len(summary['reference'])} slots, "
              f"{summary['labelled_staves']} labelled staves")
        for r in summary["proposals"]:
            conventional = CONVENTIONAL.get(r["instrument"])
            verdict = ("?" if conventional is None
                       else "OK " if r["to_clef"] in conventional else "ODD")
            total += 1
            ok += verdict == "OK "
            odd += verdict == "ODD"
            print(f"   [{verdict}] staff {r['staff_index']:2d} {r['instrument']:12s} "
                  f"{r['from_clef']}->{r['to_clef']:6s} fit {r['current_fit']:.2f}->{r['fit']:.2f} "
                  f"n={r['n_noteheads']:3d} {r['confidence_label']:6s} "
                  f"{'APPLIED' if r['applied'] else 'flag only (a reader read this clef)'}")
        applied += summary["clefs_applied"]
        restated += summary["noteheads_restated"]

    print(f"\nproposals: {total}   conventional: {ok}   unconventional: {odd}")
    print(f"applied: {applied}   noteheads restated: {restated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
