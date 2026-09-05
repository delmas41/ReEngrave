#!/usr/bin/env python3
"""Which pages actually PRINT staff labels? — measured before any transcription.

MEASUREMENT ONLY, and deliberately run FIRST. The held-out-label design needs
truth, the truth is the printed label, and a page that prints none supplies
nothing no matter how well it transcribes. Establishing that costs one staff
detection plus one Surya read per page; transcribing the same page costs ~37 s
and a detector load. Measure the truth supply before paying for the evidence.

⚠️ WHY THIS PROBE EXISTS AT ALL — a corrected assumption. The corpus was
selected on the finding that "Breitkopf labels every staff"
(`benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`). That finding was
measured on **Brahms Sämtliche Werke**, and this session treated it as a fact
about the HOUSE. It is not: a labelling convention is a property of the EDITION
/ SERIES, and Breitkopf published many. `schumann--symphony-1` (Breitkopf,
plate 8545) reads **0 labels on p.6** with 16 staves correctly detected and
Surya working.

That is the same publisher-shaped trap this corpus has sprung before, one level
finer: last time a rule transferred badly ACROSS houses (Simrock 45/45, Litolff
2/50); this time an observation failed to transfer WITHIN one house.

    python3 benchmarks/omr-staff-identity-layer-2026-09/probe_label_yield.py
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

PAGES = [1, 2, 6, 14, 22, 30]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--pages", type=int, nargs="*", default=PAGES)
    args = ap.parse_args()

    from build_calibration_corpus import resolve_corpus
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr import staff_labels_surya as S
    from tools.omr.staff_labels import has_text_layer

    corpus, missing = resolve_corpus()
    if not S.available():
        raise SystemExit("Surya unavailable; this probe would report a false "
                         "zero for every page. Refusing.")
    print(f"Surya available: True   pages probed per plate: {args.pages}\n")

    out = []
    print(f"  {'house':10s} {'work':26s} " +
          " ".join(f"{'p'+str(p):>8s}" for p in args.pages) + "   verdict")
    for house, work, plate, pdf, npages in corpus:
        cells, yields = [], []
        for pi in args.pages:
            if npages and pi >= npages:
                cells.append("     -  "); continue
            try:
                pws = detect_staves(render_page(pdf, pi, dpi=args.dpi))
                n_st = len(pws.staves)
                labs = S.read_staff_labels_surya(pws) if n_st else []
                named = sum(1 for l in labs if l.instrument)
                cells.append(f"{named:3d}/{n_st:<4d}")
                if n_st:
                    yields.append(named / n_st)
                out.append({"house": house, "work": work, "plate": plate,
                            "page": pi, "staves": n_st, "labels": len(labs),
                            "named": named,
                            "text_layer": has_text_layer(pdf, pi)})
            except Exception as exc:
                cells.append("  ERR   ")
                out.append({"house": house, "work": work, "page": pi,
                            "error": repr(exc)})
        mean = sum(yields) / len(yields) if yields else 0.0
        verdict = ("USABLE" if mean >= 0.6 else
                   "partial" if mean >= 0.25 else "NO TRUTH")
        print(f"  {house:10s} {work:26s} " +
              " ".join(f"{c:>8s}" for c in cells) +
              f"   {verdict} ({mean:.2f})")

    (HERE / "label-yield.json").write_text(json.dumps(out, indent=1))
    print(f"\n  named/staves per cell. 'USABLE' means mean named-label yield "
          f">= 0.60 across the\n  probed pages — enough printed identity to "
          f"serve as held-out truth.")


if __name__ == "__main__":
    main()
