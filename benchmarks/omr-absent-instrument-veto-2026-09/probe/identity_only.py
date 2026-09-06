"""The identity layer of a whole document, without paying for the detector.

A whole-work `transcribe` is hours of YOLO. The absent-instrument veto reads
FOUR things, none of which is a detection: each page's margin labels, the
staff→slot map, each slot's name and provenance, and the reference layout. All
four come out of `apply_contextual_analysis`, which needs only phase 1 (render +
`detect_staves`) and the label readers — call it a minute a page instead of two.

So this calls THE REAL FUNCTION with a `result` whose pages carry no staves. It
is not a reimplementation: `assign_slots`, `build_reference`, the roster, the
lexicon and the veto's own report block all run exactly as they do in a
transcription.

⚠️ WHAT IT CANNOT REPRODUCE, and it is a real limit. With no staff dicts,
`_read_clefs_by_slot` returns nothing, so `score_layouts.fit_layouts` is given
labels but no clefs. Names the SCORE-ORDER PRIOR deduces may therefore differ
from a full run's, and so may the ambiguous-alias resolutions that depend on the
fit. Names read from a LABEL — which is the only source this veto acts on, and
the source of every trombone in the bug — are untouched by that, because they
come from `build_reference` reading the margin.

So: trust this for the veto and for label-sourced names. For the emitted name of
a `score_order` staff, use a full transcription.

Usage:  identity_only.py PDF OUT.json [--dpi 600] [--pages 0-87]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.omr.assist import Assist                            # noqa: E402
from tools.omr.contextual import apply_contextual_analysis     # noqa: E402


def parse_pages(spec, n):
    if not spec:
        return list(range(n))
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main():
    pdf = sys.argv[1]
    dst = sys.argv[2]
    dpi = 600
    spec = None
    for a in sys.argv[3:]:
        if a.startswith("--dpi="):
            dpi = int(a.split("=", 1)[1])
        if a.startswith("--pages="):
            spec = a.split("=", 1)[1]
    import fitz
    with fitz.open(pdf) as doc:
        n = doc.page_count
    pages = parse_pages(spec, n)
    print(f"pdf={pdf} pages={len(pages)} of {n} dpi={dpi}", flush=True)

    result = {"source_pdf": pdf, "dpi": dpi,
              "pages": [{"page_index": i, "systems": []} for i in pages]}
    t0 = time.time()
    summary = apply_contextual_analysis(
        result, pdf_path=pdf, dpi=dpi, apply_clefs=False,
        assist=Assist("none"))
    print(f"contextual: available={summary.get('available')} "
          f"reason={summary.get('reason')} in {time.time() - t0:.0f}s",
          flush=True)
    blob = summary.get("absent_instrument_veto")
    if not blob:
        print("REFUSING: no report block — set OMR_ABSENT_INSTRUMENT_VETO=report")
        return 1
    out = {
        "source": "identity_only.py",
        "source_pdf": pdf,
        # Same shape as a transcription, so every probe here runs on it. The
        # staff records carry no `instrument`: this run has no staff dicts to
        # write one onto, and inventing one would be the reimplementation this
        # file exists to avoid.
        "pages": [{"page_index": i, "systems": []} for i in pages],
        "contextual": {k: summary.get(k) for k in (
            "reference", "absent_instrument_veto",
            "instruments_from_score_order", "instruments_from_roster",
            "ambiguous_labels_resolved", "labelled_staves",
            "unresolved_labels")},
    }
    json.dump(out, open(dst, "w"), sort_keys=True)
    print(f"wrote {dst}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
