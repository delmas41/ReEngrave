"""Per-staff, per-rung margin-label diagnostic.

Runs each rung of `contextual._labels_for_page` SEPARATELY on one page and
prints, for every staff, what each reader returned and what the lexicon makes
of it -- then what the real ladder ends up with.

The question it exists to answer: when the ladder resolves FEWER labels than
one of its own rungs alone, which rung blocked which, and on what test.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _rows(labels):
    return {lab.staff_index: (lab.text, lab.alias, lab.matched,
                              lab.confidence,
                              lab.instrument.name if lab.instrument else None)
            for lab in labels}


def _consumable(labels) -> int:
    """What a CONSUMER counts, not what the ladder's own merge counts.

    `slots.build_reference` (and every caller shaped like it) keeps a label
    only when it resolved AND its confidence is high or medium. The ladder's
    own `_usable` counts `matched` alone, so the two can disagree.
    """
    return sum(1 for lab in labels
               if lab.matched and lab.instrument
               and lab.confidence in ("high", "medium"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--json-out")
    args = ap.parse_args()

    from tools.omr import contextual
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels import read_staff_labels
    from tools.omr import staff_labels_surya, staff_labels_tesseract

    pws = detect_staves(render_page(Path(args.pdf), args.page, dpi=args.dpi))
    n = len(pws.staves)

    text = read_staff_labels(pws)
    surya = (staff_labels_surya.read_staff_labels_surya(pws)
             if staff_labels_surya.available() else [])
    tess = (staff_labels_tesseract.read_staff_labels_tesseract(pws)
            if staff_labels_tesseract.available() else [])

    tiers = [0, 0, 0, 0, 0]

    class _NoAssist:
        mode = "none"

    ladder = contextual._labels_for_page(
        pws, Path(args.pdf), args.page, assist=_NoAssist(), budget=[0],
        surya_fallback=True, ocr_fallback=True, tiers=tiers)

    t, s, x, l = (_rows(text), _rows(surya), _rows(tess), _rows(ladder))
    for name, labs in (("text", text), ("surya", surya),
                       ("tess", tess), ("LADDER", ladder)):
        print(f"{name:>7}  raw={len(labs):<3} usable(matched)="
              f"{contextual._usable(labs):<3} "
              f"consumable(high|medium)={_consumable(labs)}")
    print(f"staves={n}")
    print(f"_well_covered(text)={contextual._well_covered(text, pws)}  "
          f"_well_covered(surya)={contextual._well_covered(surya, pws)}  "
          f"tiers={tiers}")
    print()
    hdr = f"{'st':>3}  {'TEXT':<34} {'SURYA':<34} {'TESS':<28} {'LADDER'}"
    print(hdr)
    print("-" * len(hdr))

    def cell(d, i, w):
        if i not in d:
            return "-".ljust(w)
        txt, alias, matched, conf, inst = d[i]
        tag = (conf or "?")[:1] if matched else "X"
        return f"{txt!r}->{inst or alias or '?'}[{tag}]"[:w].ljust(w)

    for i in range(n):
        print(f"{i:>3}  {cell(t,i,34)} {cell(s,i,34)} {cell(x,i,28)} {cell(l,i,28)}")

    if args.json_out:
        Path(args.json_out).write_text(json.dumps({
            "pdf": args.pdf, "page": args.page, "n_staves": n,
            "rungs": {k: {str(i): list(v) for i, v in d.items()}
                      for k, d in (("text", t), ("surya", s),
                                   ("tesseract", x), ("ladder", l))},
            "usable": {"text": contextual._usable(text),
                       "surya": contextual._usable(surya),
                       "tesseract": contextual._usable(tess),
                       "ladder": contextual._usable(ladder)},
            "consumable": {"text": _consumable(text),
                           "surya": _consumable(surya),
                           "tesseract": _consumable(tess),
                           "ladder": _consumable(ladder)},
            "raw": {"text": len(text), "surya": len(surya),
                    "tesseract": len(tess), "ladder": len(ladder)},
            "well_covered_text": contextual._well_covered(text, pws),
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
