"""The pages this benchmark scores, and the facts that had to be read by eye.

Everything in here that could be derived was derived. What remains is the part
that CANNOT be: which printed staff carries which part, and how many bars are
on the page. Both were read off the scan at high zoom, and both are recorded
with the evidence that fixed them, because a later reader has no way to
re-derive them from the file.

THE BAR RANGE IS THE DANGEROUS FIELD. It is the denominator of every number
this benchmark produces, it has no independent source, and a wrong one yields a
score indistinguishable from a real one. So it is not merely asserted here — it
is cross-checked against the pipeline's own Phase 1 by `build_truth.py`, which
refuses to emit a truth file when the two disagree.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]

# The Gradus score library. `data/dossiers/` was generated from these same
# files, and PROJECT_STATUS.md sanctions the use: "The MusicXML feeds
# verification and benchmarking, not label generation."
GRADUS = Path("/Users/seanjohnson/Desktop/gradus-vercel/public/scores")

DEFAULT_WEIGHTS = REPO / "omr-weights" / "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt"


PAGES: dict[str, dict[str, Any]] = {
    "beet5-p2": {
        "work_id": "beethoven-sym5-mvt1",
        "title": "Beethoven, Symphony No. 5, Op. 67 — first movement",
        "pdf": REPO / "tools/omr/training/data/imslp/beethoven-symphony-5"
                      "/pdfs/imslp-575951/score.pdf",
        "page_index": 1,
        # 450 is the corpus convention for these two IMSLP orchestral scans:
        # it is what benchmarks/omr-corpus-sweep-2026-08/sweep.py runs them at
        # and what benchmarks/omr-key-signature/ground_truth.json records. It
        # is NOT the pipeline default (600) — see README.md, "What DPI means
        # here".
        "dpi": 450,

        # ------------------------------------------------------------------
        # HAND-READ. Bars per system, top to bottom, counted on the scan.
        # ------------------------------------------------------------------
        "systems": [17, 15],
        "first_measure": 17,   # so the page is mm.17-48; page 1 holds mm.1-16
        "n_staves": 11,

        # How the bar range was established, kept next to the number it
        # justifies. Five independent landmarks, not one count:
        "bar_range_evidence": [
            "Page 1 of the print (page_index 0) carries 16 bars: 17 full-staff "
            "ink columns on the Timpani staff, which is silent there and so has "
            "no stems to confuse a column test, and the same 17 on the Viola "
            "staff.",
            "Page 2 system 1 Timpani reads: whole rest / eighth rest + 3 eighths "
            "/ quarter+rest / quarter+rest / quarter+rest, then rests. The "
            "MusicXML has exactly that at mm.17-21. So the page opens at m.17.",
            "Page 2 system 1 Violino I landmarks all fall in the bar the "
            "17-bar count predicts: 'f' at m.19, the F# of the A-3/F#4/C5 chord "
            "at m.20, a fermata at m.21, 'ff' at m.22, a fermata at m.24 and "
            "'p' at m.25. The MusicXML marks the same six.",
            "Page 2 system 2 Flauti reads: 5 whole-bar rests, 5 quarter+rest "
            "bars under sf (the last a chord), 5 half-note bars. Flute 1 in the "
            "MusicXML is rests at mm.34-38, quarter+rest at mm.39-43 and halves "
            "at mm.44-48 — 15 bars, so the page closes at m.48.",
            "16 + 17 + 15 = 48, and the two systems' independent counts agree "
            "with the page-1 count without being fitted to it.",
        ],

        # ------------------------------------------------------------------
        # The parts scored: a MusicXML part that owns one printed staff alone.
        # `staff_ordinal` is the position within a system, top to bottom, and
        # matches benchmarks/omr-key-signature/ground_truth.json for this page.
        # ------------------------------------------------------------------
        "parts": [
            {"gradus_part": "C, G Timpani", "staff_ordinal": 6,
             "printed": "Timpani in C.G."},
            {"gradus_part": "Violin 1", "staff_ordinal": 7, "printed": "Violino I"},
            {"gradus_part": "Violin 2", "staff_ordinal": 8, "printed": "Violino II"},
            {"gradus_part": "Viola", "staff_ordinal": 9, "printed": "Viola"},
        ],

        # Every other staff, and the reason it is not scorable. Recorded rather
        # than left implicit: the excluded set is the whole reason this
        # benchmark's denominator can be trusted, and a later reader who does
        # not see it will try to "improve coverage" by putting them back.
        "excluded_staves": [
            {"staff_ordinal": 0, "printed": "Flauti",
             "parts": ["Flute 1", "Flute 2"], "why": "condensed"},
            {"staff_ordinal": 1, "printed": "Oboi",
             "parts": ["Oboe 1", "Oboe 2"], "why": "condensed"},
            {"staff_ordinal": 2, "printed": "Clarinetti in B",
             "parts": ["Bb Clarinet", "Bb Clarinet 2"], "why": "condensed"},
            {"staff_ordinal": 3, "printed": "Fagotti",
             "parts": ["Bassoon 1", "Bassoon 2"], "why": "condensed"},
            {"staff_ordinal": 4, "printed": "Corni in Es",
             "parts": ["Eb Horn 1", "Eb Horn 2"], "why": "condensed"},
            {"staff_ordinal": 5, "printed": "Trombe in C",
             "parts": ["C Trumpet 1", "C Trumpet 2"], "why": "condensed"},
            {"staff_ordinal": 10, "printed": "Violoncello e Basso",
             "parts": ["Violoncello", "Contrabass"], "why": "condensed"},
        ],
    },
}


def page_config(page_id: str) -> dict[str, Any]:
    try:
        cfg = dict(PAGES[page_id])
    except KeyError:
        raise SystemExit(
            f"unknown page {page_id!r}; known: {', '.join(sorted(PAGES))}"
        ) from None
    cfg["id"] = page_id
    cfg["last_measure"] = cfg["first_measure"] + sum(cfg["systems"]) - 1
    return cfg


def gradus_path(work_id: str) -> Path:
    for suffix in (".mxl", ".musicxml"):
        candidate = GRADUS / f"{work_id}{suffix}"
        if candidate.is_file():
            return candidate
    raise SystemExit(f"no Gradus score for {work_id} under {GRADUS}")
