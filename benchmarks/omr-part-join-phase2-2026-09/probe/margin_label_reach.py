"""REACH of the reader the staged pipeline never calls.

`gather.gather_margin_labels` abstains `not_implemented` — *"no pdf_path
supplied to gather()"* — on every staff of every staged run ever made, because
`pipeline.run_staged` uses `pdf_path` to RASTERISE and never forwards it. So
`Q.MARGIN_LABEL` has no producer, `Q.INSTRUMENT` abstains `no_evidence`, and
the part join falls to position.

⚠️ WIRING IT IS ONE LINE AND THAT IS EXACTLY WHY THE REACH MUST BE MEASURED
FIRST. CLAUDE.md already records that on this very edition *"Litolff
Beethoven's `Viola` and `Violoncello e Basso` on continuation systems"* print
no label at all — so a wired reader may still produce nothing on six of the
seven systems, and a repair that depends on names would be inert.

This drives `contextual._labels_for_page` directly, on the same pages and the
same rasterisation the record was gathered from. **No weights, no detector** —
labels are read off the margin, not off detections.

    python3 benchmarks/omr-part-join-phase2-2026-09/probe/margin_label_reach.py \
        --pages 1-4 [--surya]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

PDF = (REPO / "library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")


def parse_pages(spec: str):
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="1-4")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--surya", action="store_true")
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--pdf", default=str(PDF))
    args = ap.parse_args()

    from tools.omr.assist import Assist
    from tools.omr.contextual import _labels_for_page
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves

    print("PDF   :", args.pdf)
    print("rungs : text_layer=always  surya=%s  tesseract=%s"
          % (args.surya, args.ocr))
    print()

    total_staves = 0
    total_labels = 0
    for p in parse_pages(args.pages):
        pws = detect_staves(render_page(Path(args.pdf), p, dpi=args.dpi))
        n_staves = len(pws.staves)
        labels = _labels_for_page(pws, Path(args.pdf), p, assist=Assist("none"),
                                  budget=[0], surya_fallback=args.surya,
                                  ocr_fallback=args.ocr)
        got = [l for l in labels if (l.text or "").strip()]
        total_staves += n_staves
        total_labels += len(got)
        print("page %d: %2d staves, %2d labels" % (p, n_staves, len(got)))
        for l in got:
            print("     staff %2d  %-28r conf=%s alias=%s"
                  % (l.staff_index, l.text, getattr(l, "confidence", None),
                     getattr(l, "alias", None)))

    print()
    print("TOTAL: %d labels over %d staves" % (total_labels, total_staves))
    # ⚠️ A dead instrument must not read as a clean result. Zero labels is a
    # REAL answer here (the edition may print none on continuation systems),
    # but zero labels because no rung ran is not — and only the caller knows
    # which flags were passed, so the header above prints them.
    return 0


if __name__ == "__main__":
    sys.exit(main())
