"""Can the ENGRAVED 11-work pool price `OMR_LABEL_MERGE_QUALITY`?

Same coverage question as `probe_gate_exposure.py`, asked of the other pool.
The fixtures are LilyPond renders and therefore carry a text layer -- but a text
layer full of title, composer and music-font codepoints is not a text layer full
of MARGIN LABELS, and only the latter can gate a rung. Cheap: the text-layer
rung alone decides whether the early return can even fire.
"""
from __future__ import annotations

import argparse
from pathlib import Path

FIXTURES = Path("/Users/seanjohnson/Desktop/ReEngrave/"
                "benchmarks/omr-orchestral-e2e/fixtures")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--works", nargs="*")
    args = ap.parse_args()

    from tools.omr import contextual
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels import read_staff_labels

    pdfs = sorted(FIXTURES.glob("*.pdf"))
    if args.works:
        pdfs = [p for p in pdfs if p.stem in args.works]
    gated = []
    for pdf in pdfs:
        pws = detect_staves(render_page(pdf, 0, dpi=args.dpi))
        t = read_staff_labels(pws)
        wc = contextual._well_covered(t, pws)
        if wc:
            gated.append(pdf.stem)
        print(f"  {pdf.stem:26s} staves={len(pws.staves):>3} "
              f"text-layer labels={len(t):>3} usable={contextual._usable(t):>3} "
              f"consumable={contextual._consumable(t):>3} "
              f"well_covered={wc}")
        for lab in t[:3]:
            print(f"      {lab.text!r} -> "
                  f"{lab.instrument.name if lab.instrument else None} "
                  f"[{lab.confidence}]")
    print()
    print(f"works whose text layer can gate a free rung: {len(gated)}/{len(pdfs)}"
          + (f"  {gated}" if gated else
             "  — the engraved pool cannot exercise the early return, so a flat "
             "pooled figure there is coverage of nothing"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
