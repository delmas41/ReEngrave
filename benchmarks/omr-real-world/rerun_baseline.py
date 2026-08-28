#!/usr/bin/env python3
"""Re-run the May 2026 real-world validation on the current pipeline.

`benchmarks/omr-real-world/README.md` records a whole-pipeline measurement dated
**2026-05-22** and nothing has re-measured it since. Everything built in the
three months after — the time-signature inference layer, the five
internal-consistency checks, clef and key-signature geometry, the body-text
staff filter, staff recovery, and this branch's system grouping / slots /
instrument identity — has been measured on narrow component slices.

Component gains do not automatically compose: better clefs change pitches, which
change what rhythm and voicing see; the text filter and staff recovery change
which staves exist at all. So this asks the only question those slices cannot —
does a whole score come out better than it did in May?

Usage:
    python3 benchmarks/omr-real-world/rerun_baseline.py --out results-2026-08-28.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.omr.transcribe import transcribe

WEIGHTS = ("/Users/seanjohnson/Desktop/ReEngrave/omr-weights/"
           "deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt")
SCORES = Path("/Users/seanjohnson/Documents/Gradus-Assets/Scores/Scores For Gradus")
PDFS = Path(SCORES) / "PDF Scores"

# label, pdf, page, and the May 2026 figures from README.md.
CASES = [
    ("bach-wtc", PDFS / "IMSLP932182-PMLP5948-well-tempered-clavier-I-book.pdf", 5,
     {"systems": 5, "staves": 10, "measures": 32, "noteheads": 445}),
    ("handel-leadsheet", PDFS / "Haendel_Messiah_lead-sheet.pdf", 10,
     {"systems": 3, "staves": 15, "measures": 60, "noteheads": 298}),
    ("handel-reduction", PDFS / "Haendel_Messiah_reduction.pdf", 20,
     {"systems": 2, "staves": 12, "measures": 108, "noteheads": 476}),
    ("ravel-bolero", PDFS / "IMSLP421137-PMLP03667-Ravel_Bolero.pdf", 10,
     {"systems": 3, "staves": 32, "measures": 112, "noteheads": 1052}),
    ("beethoven-5", SCORES / "IMSLP984073-PMLP1586-symphonyno5incmi0000beet_o2b7.pdf", 15,
     {"systems": 2, "staves": 18, "measures": 98, "noteheads": 904}),
]

WARNING_KEYS = ("measure_count_warning", "key_signature_warning",
                "clef_register_warning", "time_signature_disagreement",
                "phase1_warning", "rhythm_sum_warning")


def summarize(result: dict) -> dict:
    systems = staves = measures = noteheads = pitched = timed = 0
    flags: dict[str, int] = {}
    clef_sources: dict[str, int] = {}
    for page in result.get("pages", []):
        for system in page.get("systems", []):
            systems += 1
            for staff in system.get("staves", []):
                staves += 1
                src = staff.get("clef_source") or "DEFAULTED"
                clef_sources[src] = clef_sources.get(src, 0) + 1
                for key in WARNING_KEYS:
                    if key in staff:
                        flags[key] = flags.get(key, 0) + 1
                for measure in staff.get("measures", []):
                    measures += 1
                    for key in WARNING_KEYS:
                        if key in measure:
                            flags[key] = flags.get(key, 0) + 1
                    for det in measure.get("detections", []):
                        if det.get("category") != "notehead":
                            continue
                        noteheads += 1
                        pitched += det.get("pitch") is not None
                        timed += det.get("duration_beats") is not None
    return {
        "systems": systems, "staves": staves, "measures": measures,
        "noteheads": noteheads,
        "pitched_pct": round(100 * pitched / noteheads, 1) if noteheads else 0.0,
        "timed_pct": round(100 * timed / noteheads, 1) if noteheads else 0.0,
        "clef_sources": clef_sources, "consistency_flags": flags,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    # The May README does not record its DPI. Inferred as 300: bach-wtc p5
    # gives 496 noteheads at 300 against May's 445, and 686 at 600. Running the
    # comparison at 600 inflates every count and reads as a huge regression that
    # is purely a rendering-resolution difference.
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", default=str(Path(__file__).parent / "results-2026-08-28.json"))
    ap.add_argument("--only", default=None, help="run one label")
    args = ap.parse_args()

    rows = []
    for label, pdf, page, may in CASES:
        if args.only and args.only != label:
            continue
        if not Path(pdf).exists():
            print(f"{label}: PDF not found: {pdf}", file=sys.stderr)
            continue
        t0 = time.time()
        result = transcribe(pdf_path=Path(pdf), pages=[page], weights=WEIGHTS,
                            dpi=args.dpi, imgsz=2048, progress=False)
        now = summarize(result)
        now["seconds"] = round(time.time() - t0, 1)
        rows.append({"label": label, "page": page, "may": may, "now": now})
        print(f"\n=== {label} p{page} ({now['seconds']}s) ===")
        for k in ("systems", "staves", "measures", "noteheads"):
            delta = now[k] - may[k]
            print(f"   {k:10s} May {may[k]:5d}  ->  now {now[k]:5d}   "
                  f"({delta:+d})")
        print(f"   pitched {now['pitched_pct']}%   rhythm {now['timed_pct']}%")
        print(f"   clef sources: {now['clef_sources']}")
        print(f"   consistency flags: {now['consistency_flags'] or 'none'}")

    Path(args.out).write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
