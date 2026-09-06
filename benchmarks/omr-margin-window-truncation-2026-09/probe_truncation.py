#!/usr/bin/env python3
"""Is the truncated margin label a READER fault or a PAGE fault?

`benchmarks/omr-corpus-widening-2026-09/FINDINGS.md` records margin labels that
reached the lexicon with their leading characters gone — `'larinetti in B.'`,
`'mpani in C-G'`, `'orni in F I II'` — and calls it "a reader/window fault, not
a lexicon one".

This probe asks the question the other way round: **is the missing character on
the page at all?** For each engraved benchmark fixture it reads the PDF's own
text three ways —

  1. what `staff_labels.read_staff_labels` returns (the production rung);
  2. what PyMuPDF extracts with its DEFAULT clip (the page's MediaBox);
  3. what it extracts once the MediaBox is widened to the left, which shows
     every glyph the content stream draws whether or not the sheet holds it.

A glyph present in (3) and absent from (2) is drawn at NEGATIVE x — outside the
paper — so it is neither rasterized nor extractable, and no reader window can
be blamed for missing it.

    python3 benchmarks/omr-margin-window-truncation-2026-09/probe_truncation.py \
        --fixtures benchmarks/omr-orchestral-e2e/fixtures [--staves]

`--staves` adds rung (1), which costs a phase-1 staff detection per page.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# How far left of the sheet to look for glyphs the paper does not hold.
SHIFT_PT = 400.0
# Only the left margin can hold an instrument name.
MARGIN_LIMIT_PT = 140.0


def _margin_chars(page: fitz.Page, shift: float):
    """Margin glyphs per printed line, in the shifted frame.

    `set_mediabox` re-origins the page, so a glyph the sheet drew at old x is
    reported at `old_x + shift`; `old_x = new_x - shift` recovers it.
    """
    lines: dict[float, list[tuple[float, float, str]]] = {}
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for ch in span.get("chars", []):
                    c = ch["c"]
                    if not c.strip() or ord(c) < 32:
                        continue
                    x0, y0, x1, _ = ch["bbox"]
                    if (x0 - shift) > MARGIN_LIMIT_PT:
                        continue
                    lines.setdefault(round(y0, 1), []).append((x0, x1, c))
    for chars in lines.values():
        chars.sort()
    return lines


def probe_pdf(pdf: Path) -> dict:
    doc = fitz.open(pdf)
    try:
        page = doc[0]
        w, h = page.rect.x1, page.rect.y1
        # Rung 2: the default extraction, before anything is widened.
        default_spans = []
        for block in page.get_text("dict").get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    t = (span.get("text") or "").strip()
                    if not t or span["bbox"][0] > MARGIN_LIMIT_PT:
                        continue
                    if not all(ord(c) > 31 for c in t):
                        continue
                    default_spans.append({"x0": round(span["bbox"][0], 2),
                                          "y0": round(span["bbox"][1], 2),
                                          "text": t})
        # Rung 3: widen the sheet and look again.
        page.set_mediabox(fitz.Rect(-SHIFT_PT, 0, w, h))
        truncated = []
        for key, chars in sorted(_margin_chars(page, SHIFT_PT).items()):
            whole = "".join(c for _, _, c in chars)
            shown = "".join(c for _, x1, c in chars if (x1 - SHIFT_PT) > 0.5)
            if shown != whole and len(whole) > 2:
                truncated.append({"y": key - 0.0, "full": whole,
                                  "on_the_sheet": shown,
                                  "lost": len(whole) - len(shown)})
        return {"pdf": pdf.name, "page_rect": [w, h],
                "margin_spans_default": default_spans,
                "truncated": truncated}
    finally:
        doc.close()


def with_staves(pdf: Path, dpi: int) -> list[dict]:
    """Rung 1: what the production text-layer reader returns for this page."""
    from tools.omr.preprocessing import render_page
    from tools.omr.staff_detector import detect_staves
    from tools.omr.staff_labels import read_staff_labels

    page = render_page(pdf, 0, dpi=dpi)
    pws = detect_staves(page)
    if not pws.staves:
        return []
    return [{"staff_index": lab.staff_index, "text": lab.text,
             "instrument": lab.instrument.name if lab.instrument else None,
             "confidence": lab.confidence, "alias": lab.alias}
            for lab in read_staff_labels(pws)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path,
                    default=ROOT / "benchmarks/omr-orchestral-e2e/fixtures")
    ap.add_argument("--staves", action="store_true",
                    help="also run the production reader (costs a staff detect)")
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    results = []
    for pdf in sorted(args.fixtures.glob("*.pdf")):
        if args.only and args.only not in pdf.name:
            continue
        rec = probe_pdf(pdf)
        if args.staves:
            rec["production_reader"] = with_staves(pdf, args.dpi)
        results.append(rec)

    n_trunc = sum(len(r["truncated"]) for r in results)
    n_works = sum(1 for r in results if r["truncated"])
    for r in results:
        if not (r["truncated"] or r.get("production_reader")):
            continue
        print(f"--- {r['pdf']}")
        for t in r["truncated"]:
            print(f"      lost {t['lost']}  full={t['full']!r:34} "
                  f"sheet={t['on_the_sheet']!r}")
        for lab in r.get("production_reader", []):
            if lab["instrument"] is None:
                print(f"      READER staff {lab['staff_index']}: "
                      f"{lab['text']!r} -> UNMATCHED")
    print(f"\n{n_trunc} truncated margin labels across {n_works} works "
          f"of {len(results)}")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
